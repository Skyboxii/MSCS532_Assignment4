import random
import unittest

from priority_queue import PriorityQueue, Task


def T(tid, prio, arrival=0.0, **kw):
    return Task(tid, prio, arrival_time=arrival, **kw)


class TestPriorityQueue(unittest.TestCase):
    def test_empty(self):
        pq = PriorityQueue()
        self.assertTrue(pq.is_empty())
        self.assertEqual(len(pq), 0)
        with self.assertRaises(IndexError):
            pq.extract_max()
        with self.assertRaises(IndexError):
            pq.peek()

    def test_insert_extract_max_order(self):
        pq = PriorityQueue()
        for tid, p in enumerate([5, 1, 9, 3, 7, 9, 2]):
            pq.insert(T(tid, p, arrival=tid))
            pq.check_invariants()
        out = []
        while not pq.is_empty():
            out.append(pq.extract_max().priority)
            pq.check_invariants()
        self.assertEqual(out, [9, 9, 7, 5, 3, 2, 1])

    def test_ties_are_fifo(self):
        pq = PriorityQueue()
        for tid in range(10):
            pq.insert(T(tid, 4, arrival=tid))
        self.assertEqual([pq.extract().task_id for _ in range(10)], list(range(10)))

    def test_min_heap_on_deadline(self):
        pq = PriorityQueue(kind="min", key_attr="deadline")
        for tid, d in enumerate([30, 10, 20, 5]):
            pq.insert(T(tid, 0, deadline=d))
        self.assertEqual([pq.extract_min().deadline for _ in range(4)], [5, 10, 20, 30])
        with self.assertRaises(TypeError):
            pq.extract_max()

    def test_increase_key_moves_up(self):
        pq = PriorityQueue()
        for tid, p in enumerate([10, 8, 6, 4, 2]):
            pq.insert(T(tid, p))
        pq.increase_key(4, 11)
        pq.check_invariants()
        self.assertEqual(pq.peek().task_id, 4)
        with self.assertRaises(ValueError):
            pq.increase_key(4, 1)

    def test_decrease_key_moves_down(self):
        pq = PriorityQueue()
        for tid, p in enumerate([10, 8, 6, 4, 2]):
            pq.insert(T(tid, p))
        pq.decrease_key(0, 1)
        pq.check_invariants()
        self.assertEqual(pq.peek().task_id, 1)
        with self.assertRaises(ValueError):
            pq.decrease_key(0, 5)

    def test_key_change_in_min_heap(self):
        pq = PriorityQueue(kind="min", key_attr="deadline")
        for tid, d in enumerate([1, 2, 3, 4]):
            pq.insert(T(tid, 0, deadline=d))
        pq.increase_key(0, 10)           # min-heap: larger key sinks
        pq.decrease_key(3, 0)            # smaller key rises
        pq.check_invariants()
        self.assertEqual([pq.extract().task_id for _ in range(4)], [3, 1, 2, 0])

    def test_missing_and_duplicate_ids(self):
        pq = PriorityQueue()
        pq.insert(T(1, 5))
        with self.assertRaises(ValueError):
            pq.insert(T(1, 6))
        with self.assertRaises(KeyError):
            pq.increase_key(99, 10)
        with self.assertRaises(KeyError):
            pq.remove(99)
        self.assertIn(1, pq)
        self.assertNotIn(99, pq)

    def test_remove(self):
        pq = PriorityQueue()
        for tid in range(20):
            pq.insert(T(tid, (tid * 7) % 13))
        removed = pq.remove(5)
        self.assertEqual(removed.task_id, 5)
        self.assertNotIn(5, pq)
        pq.check_invariants()
        self.assertEqual(len(pq), 19)

    def test_build_matches_inserts(self):
        tasks = [T(i, random.randint(0, 50), arrival=i) for i in range(500)]
        pq = PriorityQueue(tasks=tasks)
        pq.check_invariants()
        out = [pq.extract().task_id for _ in range(500)]
        expected = [t.task_id for t in sorted(tasks, key=lambda t: (-t.priority, t.arrival_time))]
        self.assertEqual(out, expected)

    def test_random_operations_against_reference(self):
        rng = random.Random(532)
        pq = PriorityQueue()
        ref = {}                          # task_id -> Task
        next_id = 0
        for _ in range(5000):
            op = rng.random()
            if op < 0.45 or not ref:
                t = T(next_id, rng.randint(0, 30), arrival=next_id)
                pq.insert(t)
                ref[next_id] = t
                next_id += 1
            elif op < 0.7:
                best = min(ref.values(), key=lambda t: (-t.priority, t.arrival_time, t.task_id))
                got = pq.extract_max()
                self.assertIs(got, best)
                del ref[got.task_id]
            elif op < 0.85:
                tid = rng.choice(list(ref))
                pq.increase_key(tid, ref[tid].priority + rng.randint(0, 10))
            elif op < 0.95:
                tid = rng.choice(list(ref))
                pq.decrease_key(tid, ref[tid].priority - rng.randint(0, 10))
            else:
                tid = rng.choice(list(ref))
                pq.remove(tid)
                del ref[tid]
            pq.check_invariants()
            self.assertEqual(len(pq), len(ref))

    def test_task_metrics(self):
        t = Task(1, 3, arrival_time=2, duration=4, deadline=7)
        self.assertEqual(t.base_priority, 3)
        t.start_time, t.finish_time = 5, 9
        self.assertEqual(t.waiting_time, 3)
        self.assertEqual(t.turnaround_time, 7)
        self.assertTrue(t.missed_deadline)


if __name__ == "__main__":
    unittest.main()
