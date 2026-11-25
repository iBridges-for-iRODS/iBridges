"""Dependency graph that keeps track of the dependencies between operations."""
from collections import defaultdict

from ibridges.base_operations import BaseOperation
from ibridges.exception import EmptyQueue


class DependencyGraph():
    """Class that keeps track of the dependencies between operations.

    Where the VirtualFileSystem knows which operation has which effect on the data
    (structure), for the dependency graph this is reduced to simply knowing which
    operation needs to wait for which other operation. Each operation has an operation
    id, which is how these dependencies are stored.

    The dependency graph class is self-destructive in the sense that the operations will move from
    the queue to the running operations and then removed.
    """

    def __init__(self):
        """Initialize empty dependency graph."""
        self.dependency_of  = defaultdict(set)
        self.depends_on = {}
        self.queue = []  # All operations that can be scheduled if there are sufficient resources
        self.running = set()  # All operations that are currently running
        self.operations: dict[int, BaseOperation] = {}  # All operations in any state
        self.skipped_operation: list[BaseOperation] = []  # All operations that were skipped

    def add(self, op: BaseOperation, depends_on: list[int], skip: bool = False):
        """Add a new operation to the dependency graph.

        Parameters
        ----------
        op:
            Operation to be added.
        depends_on:
            List of operation IDs of operations on which the current operation depends.
        skip:
            Whether to skip the operation.

        """
        if skip:
            self.skipped_operation.append(op)
            return

        op_id = len(self.operations)
        self.operations[op_id] = op
        self.depends_on[op_id] = depends_on
        for other_op_id in depends_on:
            self.dependency_of[other_op_id].add(op_id)
        if len(depends_on) == 0:
            self.queue.append(op_id)

    def next_op(self) -> tuple[BaseOperation, int]:
        """Get the next operation out of the queue.

        Raises
        ------
        EmptyQueue:
            If the queue is empty. This can happen if there are no more items to be scheduled,
            or if the leftover items all have to wait on operations that are currently running.

        Returns
        -------
        op:
            Operation that needs to be executed.
        op_id:
            The operation ID of the operation to be run.

        """
        if len(self.queue) == 0:
            raise EmptyQueue()

        op_id = self.queue.pop()
        self.running.add(op_id)
        return self.operations[op_id], op_id

    def finish_op(self, op_id: int):
        """Finish the operation and remove it from the queue.

        This should be called after the operation has finished running by one of the workers.

        Parameters
        ----------
        op_id:
            The operation ID to finish.

        """
        self.running.remove(op_id)
        for dep_op_id in self.dependency_of[op_id]:
            self.depends_on[dep_op_id].remove(op_id)
            if len(self.depends_on[dep_op_id]) == 0:
                self.queue.append(dep_op_id)
        self.depends_on.pop(op_id)
        self.dependency_of.pop(op_id, None)

    @property
    def total_size(self) -> int:
        """Get the total size of not skipped operations.

        Returns
        -------
            The number of bytes of all operations.

        """
        return sum(op.size for op in self.operations.values())

    def __len__(self) -> int:
        """Get the number of operations that are still to be scheduled."""
        return len(self.depends_on)

    def print_summary(self):
        """Print a summary of all operations to be executed."""
        op_dict = defaultdict(list)
        for op in self.operations.values():
            op_dict[op.header].append(op)

        skipped_dict = defaultdict(lambda: 0)
        for op in self.skipped_operation:
            skipped_dict[op.header] += 1

        op_texts = []
        for header in (set(op_dict) | set(skipped_dict)):
            cur_text = f"{header}:\n\n"
            if header in op_dict:
                for op in op_dict[header]:
                    cur_text += op.body + "\n"
            if header in skipped_dict:
                cur_text += f"Skipped: {skipped_dict[header]}"
            op_texts.append(cur_text)
        print("\n\n".join(op_texts))
