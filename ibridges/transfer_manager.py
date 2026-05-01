from __future__ import annotations

import json
import warnings
from collections import defaultdict
from enum import Enum
from inspect import signature
from multiprocessing import Queue, Process
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from tqdm import tqdm

from ibridges.base_operations import DependencyGraph, SkipOperation, VirtualFileSystem

# if TYPE_CHECKING:
from ibridges.session import Session

NUM_THREADS = 4


class TransferManager():
    def __init__(self, session: Session, resc_name: Optional[str] = None,
                 options: Optional[dict] = None, n_workers: int = 4):
        self.session = session
        self.local_vfs = VirtualFileSystem()
        self.remote_vfs = VirtualFileSystem()
        self.operations = {}
        self.dep_graph = DependencyGraph()
        self.worker_queue = None
        self.scheduler_queue = None
        self.n_skipped = defaultdict(lambda: 0)
        self.n_workers = n_workers

    def add(self, op):
        op_id = len(self.operations)
        try:
            deps = op.add_to_vfs(self.local_vfs, self.remote_vfs, op_id, self.session)
        except SkipOperation:
            self.n_skipped[op.header] += 1
            return

        self.dep_graph.add(op_id, deps)
        self.operations[op_id] = op

    def execute_singlethreaded(self):
        while len(self.dep_graph):
            op_id = self.dep_graph.next_op()
            op = self.operations.pop(op_id)
            op.execute(self.session)
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
                    args=(worker_queue, scheduler_queue, self.session.copy_param)))
            self.worker_processes[-1].start()
            # )
        # self.worker_processes = [
            # 
                # for _ in range(self.n_workers)]
        while len(self.dep_graph) > 0:
            try:
                while True:
                    op_id = self.dep_graph.next_op()
                    op = self.operations.pop(op_id)
                    worker_queue.put((op, op_id))
            except IndexError:
                pass
            dep_graph_updated = False
            while not dep_graph_updated:
                msg = scheduler_queue.get()
                print(msg)
                if msg["msg_type"] == "progress":
                    pbar.update(msg["value"])
                else:
                    self.dep_graph.finish_op(msg["id"])
                    dep_graph_updated = True

        for _ in range(self.n_workers):
            worker_queue.put(None)

        for worker in self.worker_processes:
            worker.join()


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


def executor_worker(queue, scheduler_queue, session_param):
    session = session_param[0](*session_param[1:])
    i=0
    pbar = PBar(scheduler_queue)
    while True:
        order = queue.get()
        if order is None:
            session.close()
            break
        op, op_id = order
        op.execute(pbar=pbar)
        scheduler_queue.put({"msg_type": "finish", "id": op_id})
        i += 1

def scheduler(queue, worker_queue, n_workers, dep_graph, operations):
    finished_orders = set()
    waiting_orders = defaultdict(list)
    n_orders = 0
    queue_finished = False
    pbar = tqdm(
        total=0,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        # disable=disable,
    )
    while True:
        
        if queue_finished and len(finished_orders) == n_orders:
            for i in range(n_workers):
                worker_queue.put(None)
            break

        order = queue.get()
        if order is None:
            queue_finished = True
            continue
        op_type = order["op_type"]
        if op_type == "download":
            n_orders += 1
            size = order.get("size", 1)
            pbar.total += size
            pbar.refresh()
            depends = order.get("depends", None)
            if depends is None or depends in finished_orders:
                worker_queue.put(order)
            else:
                waiting_orders[depends].append(order)
        elif op_type == "finish":
            op_id = order["id"]
            finished_orders.add(op_id)
            if op_id in waiting_orders:
                for new_order in waiting_orders[op_id]:
                    worker_queue.put(new_order)
                del waiting_orders[op_id]
        elif op_type == "progress":
            pbar.update(order["value"])
        else:
            raise ValueError(f"Unknown operation type {op_type}")
