"""
Priority queue of tasks backed by a binary heap stored in a Python list.

Follows Cormen, Leiserson, Rivest, & Stein, Introduction to Algorithms
(4th ed.), Section 6.5 (Priority queues): MAX-HEAP-INSERT,
MAX-HEAP-EXTRACT-MAX, MAX-HEAP-INCREASE-KEY, and their min-heap mirrors.

Design
------
* The heap is a plain Python list.  The tree is implicit: the children of
  index i are 2i+1 and 2i+2 and its parent is (i-1)//2, so no node objects
  or pointers are needed, the data is contiguous, and append/pop at the end
  are amortized O(1).
* kind="max" serves the LARGEST key first (priority scheduling: a higher
  number means more urgent).  kind="min" serves the SMALLEST key first
  (earliest-deadline-first, or FIFO by arrival time).
* key_attr names the Task field used as the key ("priority" by default,
  "deadline" for EDF, "arrival_time" for FIFO).
* Ties are broken by arrival time, then task_id, so tasks with equal keys
  leave in first-come-first-served order and every run is deterministic.
* A dictionary maps task_id -> index in the list and is updated on every
  swap.  That lets increase_key / decrease_key find a task in O(1) instead
  of an O(n) search, so changing a key costs only the O(lg n) sift.

Operation costs (n = number of tasks in the queue)
--------------------------------------------------
    insert            O(lg n)    sift up from a new leaf
    extract_max/min   O(lg n)    move last leaf to the root, sift down
    increase/decrease_key O(lg n) O(1) lookup + one sift
    remove            O(lg n)
    peek, is_empty, len, contains   O(1)
    build             O(n)       bottom-up heapify (CLRS BUILD-MAX-HEAP)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """One unit of work to schedule.

    priority      current priority (higher = more urgent); aging may raise it
    base_priority priority the task arrived with (set automatically)
    arrival_time  when the task enters the system
    duration      how long it runs once started (non-preemptive)
    deadline      absolute time by which it should finish
    start_time / finish_time are filled in by the scheduler.
    """
    task_id: int
    priority: float
    arrival_time: float = 0.0
    duration: float = 1.0
    deadline: float = float("inf")
    name: str = ""
    base_priority: Optional[float] = None
    start_time: Optional[float] = field(default=None, compare=False)
    finish_time: Optional[float] = field(default=None, compare=False)

    def __post_init__(self):
        if self.base_priority is None:
            self.base_priority = self.priority

    @property
    def waiting_time(self):
        return None if self.start_time is None else self.start_time - self.arrival_time

    @property
    def turnaround_time(self):
        return None if self.finish_time is None else self.finish_time - self.arrival_time

    @property
    def missed_deadline(self):
        return self.finish_time is not None and self.finish_time > self.deadline


class PriorityQueue:
    """Binary-heap priority queue of Task objects (see module docstring)."""

    def __init__(self, kind="max", key_attr="priority", tasks=None):
        if kind not in ("max", "min"):
            raise ValueError("kind must be 'max' or 'min'")
        self.kind = kind
        self.key_attr = key_attr
        self._heap = []            # the array: _heap[0] is the root
        self._pos = {}             # task_id -> index in _heap
        if tasks:
            self.build(tasks)

    # ------------------------------------------------------------------
    # Ordering and index helpers
    # ------------------------------------------------------------------

    def _key(self, task):
        return getattr(task, self.key_attr)

    def _before(self, a, b):
        """True if task a must leave the queue before task b."""
        ka, kb = self._key(a), self._key(b)
        if ka != kb:
            return ka > kb if self.kind == "max" else ka < kb
        if a.arrival_time != b.arrival_time:       # tie: first come, first served
            return a.arrival_time < b.arrival_time
        return a.task_id < b.task_id

    def _swap(self, i, j):
        h = self._heap
        h[i], h[j] = h[j], h[i]
        self._pos[h[i].task_id] = i                # keep the index map in sync
        self._pos[h[j].task_id] = j

    def _sift_up(self, i):
        """Move h[i] up while it should leave before its parent: O(lg n)."""
        while i > 0:
            parent = (i - 1) // 2
            if not self._before(self._heap[i], self._heap[parent]):
                break
            self._swap(i, parent)
            i = parent
        return i

    def _sift_down(self, i):
        """Move h[i] down below any child that should leave first: O(lg n)."""
        h, n = self._heap, len(self._heap)
        while True:
            left, right = 2 * i + 1, 2 * i + 2
            best = i
            if left < n and self._before(h[left], h[best]):
                best = left
            if right < n and self._before(h[right], h[best]):
                best = right
            if best == i:
                return i
            self._swap(i, best)
            i = best

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def insert(self, task):
        """Add a task: append it as a new leaf, then sift it up.  O(lg n)."""
        if task.task_id in self._pos:
            raise ValueError("task_id {} is already in the queue".format(task.task_id))
        self._heap.append(task)
        self._pos[task.task_id] = len(self._heap) - 1
        self._sift_up(len(self._heap) - 1)

    def peek(self):
        """Return (without removing) the next task to be served.  O(1)."""
        if not self._heap:
            raise IndexError("peek from an empty priority queue")
        return self._heap[0]

    def extract(self):
        """
        Remove and return the next task to be served: the root.  The last
        leaf replaces the root and sifts down.  O(lg n).
        """
        if not self._heap:
            raise IndexError("extract from an empty priority queue")
        top = self._heap[0]
        last = self._heap.pop()
        del self._pos[top.task_id]
        if self._heap:                       # if top was not the only task
            self._heap[0] = last
            self._pos[last.task_id] = 0
            self._sift_down(0)
        return top

    def extract_max(self):
        """Remove and return the task with the highest key (max-heap)."""
        if self.kind != "max":
            raise TypeError("extract_max() requires kind='max'")
        return self.extract()

    def extract_min(self):
        """Remove and return the task with the lowest key (min-heap)."""
        if self.kind != "min":
            raise TypeError("extract_min() requires kind='min'")
        return self.extract()

    def increase_key(self, task_id, new_key):
        """
        Raise a task's key to new_key.  In a max-heap the task can only move
        toward the root (sift up); in a min-heap only toward the leaves
        (sift down).  O(1) lookup via the index map + O(lg n) sift.
        """
        task = self._get(task_id)
        if new_key < self._key(task):
            raise ValueError("new key is smaller than the current key")
        return self._set_key(task, new_key)

    def decrease_key(self, task_id, new_key):
        """Lower a task's key to new_key (mirror of increase_key).  O(lg n)."""
        task = self._get(task_id)
        if new_key > self._key(task):
            raise ValueError("new key is larger than the current key")
        return self._set_key(task, new_key)

    def change_key(self, task_id, new_key):
        """Set a task's key to any value and restore the heap.  O(lg n)."""
        return self._set_key(self._get(task_id), new_key)

    def remove(self, task_id):
        """Delete an arbitrary task (e.g., a cancelled job).  O(lg n)."""
        if task_id not in self._pos:
            raise KeyError(task_id)
        i = self._pos[task_id]
        last_index = len(self._heap) - 1
        if i != last_index:
            self._swap(i, last_index)
        task = self._heap.pop()
        del self._pos[task_id]
        if i < len(self._heap):              # the moved task may go up or down
            self._sift_down(self._sift_up(i))
        return task

    def is_empty(self):
        """True if no tasks are waiting.  O(1)."""
        return not self._heap

    def build(self, tasks):
        """
        Replace the contents with tasks and heapify bottom-up in O(n)
        (CLRS BUILD-MAX-HEAP), which beats n separate inserts (O(n lg n)).
        """
        self._heap = list(tasks)
        self._pos = {}
        for i, t in enumerate(self._heap):
            if t.task_id in self._pos:
                raise ValueError("duplicate task_id {}".format(t.task_id))
            self._pos[t.task_id] = i
        for i in range(len(self._heap) // 2 - 1, -1, -1):
            self._sift_down(i)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, task_id):
        try:
            return self._heap[self._pos[task_id]]
        except KeyError:
            raise KeyError(task_id) from None

    def _set_key(self, task, new_key):
        setattr(task, self.key_attr, new_key)
        i = self._pos[task.task_id]
        # Exactly one of these moves the task (or neither, if the key is equal).
        return self._sift_down(self._sift_up(i))

    def get(self, task_id):
        """Return the queued task with this id (O(1)); KeyError if absent."""
        return self._get(task_id)

    def tasks(self):
        """Snapshot list of the queued tasks, in heap (not sorted) order."""
        return list(self._heap)

    def __len__(self):
        return len(self._heap)

    def __contains__(self, task_id):
        return task_id in self._pos

    def __bool__(self):
        return bool(self._heap)

    def check_invariants(self):
        """Assert the heap property and index map (used by the tests)."""
        h = self._heap
        for i in range(1, len(h)):
            assert not self._before(h[i], h[(i - 1) // 2]), "heap property violated at %d" % i
        assert len(self._pos) == len(h)
        for i, t in enumerate(h):
            assert self._pos[t.task_id] == i, "index map wrong for task %r" % t.task_id

    def __repr__(self):
        return "PriorityQueue(kind={!r}, key_attr={!r}, size={})".format(
            self.kind, self.key_attr, len(self))


if __name__ == "__main__":
    pq = PriorityQueue(kind="max")
    for tid, prio, arrive in [(1, 3, 0), (2, 9, 1), (3, 5, 2), (4, 9, 3), (5, 1, 4)]:
        pq.insert(Task(tid, prio, arrival_time=arrive))
    print(pq, "| next:", pq.peek().task_id)
    pq.increase_key(5, 10)                 # task 5 becomes the most urgent
    pq.decrease_key(2, 2)                  # task 2 drops behind the others
    order = []
    while not pq.is_empty():
        t = pq.extract_max()
        order.append((t.task_id, t.priority))
    print("extraction order (id, priority):", order)
