"""Transfer manager module that enables single and multithreaded/multiprocessing."""
from __future__ import annotations

import queue
from collections import defaultdict
from multiprocessing import Process, Queue
from threading import Thread

from tqdm import tqdm

from ibridges.base_operations import (
    BaseOperation,
    DependencyGraph,
    SkipOperation,
    VirtualFileSystem,
)
from ibridges.session import Session


class TransferManager():  # pylint: disable=too-many-instance-attributes
    """Manager for transfers that has multithreading capabilities."""

    def __init__(self, session: Session, n_workers: int = 8,
                 threads_per_transfer: int = 4, parallel_method: str = "thread",
                 progress_bar: bool = True):
        """Initialize the transfer manager.

        Parameters
        ----------
        session
            The session to use for the operations.
        resc_name
            Resource name for the transfers, by default None
        options
            Options to be used for the transfers, by default None
        n_workers
            Number of total threads/processes to use, by default 8.
            Can be slightly higher in practice.
        threads_per_transfer
            Maximum number of threads used per transfer, by default 4
        parallel_method
            Whether to use threads ("thread") or processes ("process"), by default "thread".
            The advantage of using threads is that the current session can be used, while the
            process method will start up as many sessions as workers.
        progress_bar:
            Whether to use a progress bar.

        """
        self.session = session
        self.local_vfs = VirtualFileSystem()
        self.remote_vfs = VirtualFileSystem()
        self.operations: dict[int, BaseOperation] = {}
        self.dep_graph = DependencyGraph()
        self.n_skipped: dict[str, int] = defaultdict(lambda: 0)
        self.n_workers = n_workers
        self.threads_per_transfer = threads_per_transfer
        self.parallel_method=parallel_method
        self.progress_bar = progress_bar

    def add(self, op: BaseOperation):
        """Add an operation to the queue or skip the operation.

        Parameters
        ----------
        op
            Operation to be added to the dependency graph.

        """
        op_id = len(self.operations)
        try:
            deps = op.add_to_vfs(self.local_vfs, self.remote_vfs, op_id)
        except SkipOperation:
            self.n_skipped[op.header] += 1
            return

        self.dep_graph.add(op_id, deps)
        self.operations[op_id] = op

    def execute(self):
        """Execute all operations."""
        if self.n_workers == 1:
            self.execute_singlethreaded()
        elif self.parallel_method == "thread":
            self.execute_multithreading()
        elif self.parallel_method == "process":
            self.execute_multiprocess()
        else:
            raise ValueError(f"Unknown method of execution: {self.parallel_method}")

    def execute_singlethreaded(self):
        """Execute all operations single threaded."""
        total_size = sum(op.size for op in self.operations.values())
        pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            disable=not self.progress_bar,
        )
        while len(self.dep_graph):
            op_id = self.dep_graph.next_op()
            op = self.operations.pop(op_id)
            op.execute(self.session, pbar, self.threads_per_transfer)
            self.dep_graph.finish_op(op_id)

    def execute_multiprocess(self):
        """Execute all operations using multiprocessing."""
        worker_queue = Queue()
        scheduler_queue = Queue()
        total_size = sum(op.size for op in self.operations.values())
        pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            disable=not self.progress_bar,
        )
        worker_processes = []
        for _ in range(self.n_workers):
            worker_processes.append(
                Process(target=_executor_worker_process,
                    args=(worker_queue, scheduler_queue, self.session.copy_param,
                          self.threads_per_transfer)))
            worker_processes[-1].start()

        running_operations = {}
        threads_used = 0
        while len(self.dep_graph) > 0:
            try:
                while threads_used < self.n_workers:
                    op_id = self.dep_graph.next_op()
                    op = self.operations.pop(op_id)
                    running_operations[op_id] = op
                    if hasattr(op, "ipath"):
                        op.ipath.session = None
                    worker_queue.put((op, op_id))
                    threads_used += op.threads(self.threads_per_transfer)
            except IndexError:
                pass
            dep_graph_updated = False
            while not dep_graph_updated:
                msg = scheduler_queue.get()
                if msg["msg_type"] == "progress":
                    pbar.update(msg["value"])
                else:
                    self.dep_graph.finish_op(msg["id"])
                    dep_graph_updated = True
                    op = running_operations.pop(msg["id"])
                    threads_used -= op.threads(self.threads_per_transfer)

        for _ in range(self.n_workers):
            worker_queue.put(None)

        for worker in worker_processes:
            worker.join()
        pbar.close()


    def execute_multithreading(self):
        """Execute all operations using multithreading."""
        worker_queue = queue.Queue()
        scheduler_queue = queue.Queue()
        total_size = sum(op.size for op in self.operations.values())
        pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            disable=not self.progress_bar,
        )
        worker_threads = []
        for _ in range(self.n_workers):
            worker_threads.append(
                Thread(target=_executor_worker_thread,
                    args=(worker_queue, scheduler_queue, self.session, self.threads_per_transfer)))
            worker_threads[-1].start()
        running_operations = {}
        threads_used = 0
        while len(self.dep_graph) > 0:
            try:
                while threads_used < self.n_workers:
                    op_id = self.dep_graph.next_op()
                    op = self.operations.pop(op_id)
                    running_operations[op_id] = op
                    if hasattr(op, "ipath"):
                        op.ipath.session = None
                    worker_queue.put((op, op_id))
                    threads_used += op.threads(self.threads_per_transfer)
            except IndexError:
                pass
            dep_graph_updated = False
            while not dep_graph_updated:
                msg = scheduler_queue.get()
                if msg["msg_type"] == "progress":
                    pbar.update(msg["value"])
                else:
                    self.dep_graph.finish_op(msg["id"])
                    dep_graph_updated = True
                    op = running_operations.pop(msg["id"])
                    threads_used -= op.threads(self.threads_per_transfer)

        for _ in range(self.n_workers):
            worker_queue.put(None)

        for worker in worker_threads:
            worker.join()
        pbar.close()

    def print_summary(self):
        """Print a summary of all operations to be executed."""
        op_dict = defaultdict(list)
        for op in self.operations.values():
            op_dict[op.header].append(op)

        only_skipped = set(self.n_skipped.keys()) - set(op_dict.keys())
        for header in only_skipped:
            op_dict[header] = []

        for header, op_list in op_dict.items():
            print(f"{header}:")
            if len(op_list) > 0:
                print("\n")
            for op in op_list:
                print(f"{op.body}")
            print(f"\nSkipped: {self.n_skipped.get(header, 0)}\n\n")


class PBar():  # pylint: disable=too-few-public-methods
    """Multithreading/processing progress bar that uses a queue to pass the message."""

    def __init__(self, update_queue):
        """Initialize progress bar and connect to the queue."""
        self.queue = update_queue

    def update(self, value: int):
        """Update the progress bar by that many ticks/bytes.

        Parameters
        ----------
        value:
            Number of bytes that has been processed.

        """
        self.queue.put({"msg_type": "progress", "value": value})


def _executor_worker_process(job_queue: Queue, scheduler_queue: Queue, session_param: list,
                             n_threads: int):
    """Worker for multiprocessing parallization."""
    session = session_param[0](*session_param[1:])
    i=0
    pbar = PBar(scheduler_queue)
    while True:
        order = job_queue.get()
        if order is None:
            session.close()
            break
        op, op_id = order
        if hasattr(op, "ipath"):
            op.ipath.session = session
        op.execute(session, pbar=pbar, n_threads=n_threads)
        scheduler_queue.put({"msg_type": "finish", "id": op_id})
        i += 1

def _executor_worker_thread(job_queue: queue.Queue, scheduler_queue: queue.Queue, session: Session,
                            n_threads: int):
    """Worker for multithreading parallelization."""
    i=0
    pbar = PBar(scheduler_queue)
    while True:
        order = job_queue.get()
        if order is None:
            break
        op, op_id = order
        if hasattr(op, "ipath"):
            op.ipath.session = session
        op.execute(session, pbar=pbar, n_threads=n_threads)
        scheduler_queue.put({"msg_type": "finish", "id": op_id}, block=False)
        i += 1
