from __future__ import annotations

import json
import queue
import warnings
from collections import defaultdict
from enum import Enum
from inspect import signature
from multiprocessing import Process, Queue
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Optional, Union

from tqdm import tqdm

from ibridges.base_operations import DependencyGraph, SkipOperation, VirtualFileSystem
from ibridges.session import Session

NUM_THREADS = 4


class TransferManager():
    def __init__(self, session: Session, resc_name: Optional[str] = None,
                 options: Optional[dict] = None, n_workers: int = 8,
                 threads_per_transfer: int = 4, parallel_method: str = "thread"):
        self.session = session
        self.local_vfs = VirtualFileSystem()
        self.remote_vfs = VirtualFileSystem()
        self.operations = {}
        self.dep_graph = DependencyGraph()
        self.worker_queue = None
        self.scheduler_queue = None
        self.n_skipped = defaultdict(lambda: 0)
        self.n_workers = n_workers
        self.threads_per_transfer = threads_per_transfer
        self.parallel_method=parallel_method

    def add(self, op):
        op_id = len(self.operations)
        try:
            deps = op.add_to_vfs(self.local_vfs, self.remote_vfs, op_id)
        except SkipOperation:
            self.n_skipped[op.header] += 1
            return

        self.dep_graph.add(op_id, deps)
        self.operations[op_id] = op

    def execute(self):
        if self.n_workers == 1:
            self.execute_singlethreaded()
        elif self.parallel_method == "thread":
            self.execute_multi()
        else:
            self.execute_multithreaded()

    def execute_singlethreaded(self):
        total_size = sum(op.size for op in self.operations.values())
        pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            # disable=disable,
        )
        while len(self.dep_graph):
            op_id = self.dep_graph.next_op()
            op = self.operations.pop(op_id)
            op.execute(self.session, pbar, self.threads_per_transfer)
            self.dep_graph.finish_op(op_id)

    def execute_multithreaded(self):
        worker_queue = Queue()
        scheduler_queue = Queue()
        total_size = sum(op.size for op in self.operations.values())
        pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            # disable=disable,
        )
        self.worker_processes = []
        for _ in range(self.n_workers):
            self.worker_processes.append(
                Process(target=executor_worker,
                    args=(worker_queue, scheduler_queue, self.session.copy_param, self.threads_per_transfer)))
            self.worker_processes[-1].start()

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

        for worker in self.worker_processes:
            worker.join()
        pbar.close()


    def execute_multi(self):
        worker_queue = queue.Queue()
        scheduler_queue = queue.Queue()
        total_size = sum(op.size for op in self.operations.values())
        pbar = tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            # disable=disable,
        )
        self.worker_threads = []
        for _ in range(self.n_workers):
            self.worker_threads.append(
                Thread(target=executor_worker_thread,
                    args=(worker_queue, scheduler_queue, self.session, self.threads_per_transfer)))
            self.worker_threads[-1].start()
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

        for worker in self.worker_threads:
            worker.join()
        pbar.close()

    def print_summary(self):
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


class PBar():
    def __init__(self, queue):
        self.queue = queue

    def update(self, value):
        self.queue.put({"msg_type": "progress", "value": value})


def executor_worker(queue, scheduler_queue, session_param, n_threads):
    import numpy as np
    worker_id = np.random.randint(0, 1000)
    
    session = session_param[0](*session_param[1:])
    i=0
    pbar = PBar(scheduler_queue)
    while True:
        order = queue.get()
        if order is None:
            session.close()
            break
        op, op_id = order
        if hasattr(op, "ipath"):
            op.ipath.session = session
        op.execute(session, pbar=pbar, n_threads=n_threads)
        scheduler_queue.put({"msg_type": "finish", "id": op_id})
        i += 1

def executor_worker_thread(queue, scheduler_queue, session, n_threads):
    import numpy as np
    worker_id = np.random.randint(0, 1000)
    i=0
    pbar = PBar(scheduler_queue)
    while True:
        order = queue.get()
        if order is None:
            break
        op, op_id = order
        if hasattr(op, "ipath"):
            op.ipath.session = session
        # print(worker_id, op_id, "start execution")
        op.execute(session, pbar=pbar, n_threads=n_threads)
        # print(worker_id, op_id, "Finished execution")
        scheduler_queue.put({"msg_type": "finish", "id": op_id}, block=False)
        i += 1
