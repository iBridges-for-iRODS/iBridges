"""Transfer manager module that enables single and multithreaded/multiprocessing."""
from __future__ import annotations

import queue
from multiprocessing import Process, Queue
from threading import Thread

from tqdm import tqdm

from ibridges.base_operations import (
    BaseOperation,
    DependencyGraph,
    EmptyQueue,
    SkipOperation,
    VirtualFileSystem,
)
from ibridges.session import Session


class TransferManager():  # pylint: disable=too-many-instance-attributes
    """Manager for transfers that has multithreading capabilities."""

    def __init__(self, session: Session, n_workers: int = 1,
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
        self.dep_graph = DependencyGraph()
        self.n_workers = n_workers
        self.threads_per_transfer = threads_per_transfer
        self.parallel_method = parallel_method
        self.progress_bar = progress_bar

    def add(self, op: BaseOperation):
        """Add an operation to the queue or skip the operation.

        Parameters
        ----------
        op
            Operation to be added to the dependency graph.

        """
        if not isinstance(op, BaseOperation):
            raise ValueError(f"{op} is not an operation!")
        skip = False
        try:
            deps = op.add_to_vfs(self.local_vfs, self.remote_vfs, len(self.dep_graph.operations))
        except SkipOperation:
            deps = None
            skip = True

        self.dep_graph.add(op, deps, skip=skip)

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
        pbar = tqdm(
            total=self.dep_graph.total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            disable=not self.progress_bar,
        )
        while len(self.dep_graph):
            op, op_id = self.dep_graph.next_op()
            op.execute(self.session, pbar, self.threads_per_transfer)
            self.dep_graph.finish_op(op_id)

    def execute_multiprocess(self):
        """Execute all operations using multiprocessing."""
        worker_queue = Queue()
        scheduler_queue = Queue()
        pbar = tqdm(
            total=self.dep_graph.total_size,
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

        threads_used = 0
        error = None
        while len(self.dep_graph) > 0 and error is None:
            try:
                while threads_used < self.n_workers:
                    op, op_id = self.dep_graph.next_op()
                    n_threads = op.threads(self.threads_per_transfer)
                    worker_queue.put((op.pack(), op_id))
                    threads_used += n_threads
            except EmptyQueue:
                pass
            dep_graph_updated = False
            while not dep_graph_updated and error is None:
                msg = scheduler_queue.get()
                if msg["msg_type"] == "progress":
                    pbar.update(msg["value"])
                else:
                    self.dep_graph.finish_op(msg["id"])
                    dep_graph_updated = True
                    op = self.dep_graph.operations[op_id]
                    threads_used -= op.threads(self.threads_per_transfer)
                    if msg["msg_type"] == "error":
                        error = msg["error"]

        if error is not None:
            for worker in worker_processes:
                worker.terminate()
            raise error

        for _ in range(self.n_workers):
            worker_queue.put(None)

        for worker in worker_processes:
            worker.join()
        worker_queue.close()
        scheduler_queue.close()

        pbar.close()


    def execute_multithreading(self):
        """Execute all operations using multithreading."""
        worker_queue = queue.Queue()
        scheduler_queue = queue.Queue()
        pbar = tqdm(
            total=self.dep_graph.total_size,
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

        threads_used = 0
        while len(self.dep_graph) > 0:
            try:
                while threads_used < self.n_workers:
                    op, op_id = self.dep_graph.next_op()
                    n_threads = op.threads(self.threads_per_transfer)
                    worker_queue.put((op.pack(), op_id))
                    threads_used += n_threads
            except EmptyQueue:
                pass
            dep_graph_updated = False
            while not dep_graph_updated:
                msg = scheduler_queue.get()
                if msg["msg_type"] == "progress":
                    pbar.update(msg["value"])
                else:
                    self.dep_graph.finish_op(msg["id"])
                    dep_graph_updated = True
                    op = self.dep_graph.operations[op_id]
                    threads_used -= op.threads(self.threads_per_transfer)
                    if msg["msg_type"] == "error":
                        raise msg["error"]

        for _ in range(self.n_workers):
            worker_queue.put(None)

        for worker in worker_threads:
            worker.join()
        pbar.close()

    def print_summary(self):
        """Print a summary of all operations to be executed."""
        self.dep_graph.print_summary()

    def get_operations(self, op_type: str):
        """Get operation of a certain type."""
        return [op for op in self.dep_graph.operations.values() if op.__class__.__name__ == op_type]

    def __getattribute__(self, key):
        """Add upload/download/create_collection/create_dir attributes."""
        if key == "upload":
            return self.get_operations("UploadOperation")
        if key == "download":
            return self.get_operations("DownloadOperation")
        if key == "create_collection":
            return self.get_operations("CreateCollectionOperation")
        if key == "create_dir":
            return self.get_operations("CreateDirectoryOperation")
        return super().__getattribute__(key)

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
        packed_op, op_id = order
        op = packed_op.unpack(session)
        try:
            op.execute(session, pbar=pbar, n_threads=n_threads)
            scheduler_queue.put({"msg_type": "finish", "id": op_id})
        except Exception as exc:  # pylint: disable=broad-exception-caught
            scheduler_queue.put({"msg_type": "error", "id": op_id, "error": exc})
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
        packed_op, op_id = order
        op = packed_op.unpack(session)
        try:
            op.execute(session, pbar=pbar, n_threads=n_threads)
            scheduler_queue.put({"msg_type": "finish", "id": op_id}, block=False)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            scheduler_queue.put({"msg_type": "error", "id": op_id, "error": exc})
        i += 1
