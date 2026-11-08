import unittest

from priority_queue import Task
from scheduler import MAX_PRIORITY, POLICIES, generate_workload, simulate, summarize


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.workload = generate_workload(n=400, load=0.95, seed=7)

    def check_schedule(self, finished, n):
        self.assertEqual(len(finished), n)
        self.assertEqual(len({t.task_id for t in finished}), n)
        prev_finish = 0.0
        for t in finished:                     # finished is in run order
            self.assertGreaterEqual(t.start_time, t.arrival_time)
            self.assertGreaterEqual(t.start_time, prev_finish)   # one task at a time
            self.assertAlmostEqual(t.finish_time - t.start_time, t.duration)
            prev_finish = t.finish_time

    def test_every_policy_produces_valid_schedule(self):
        for policy in POLICIES:
            with self.subTest(policy=policy):
                finished, ops = simulate(self.workload, policy)
                self.check_schedule(finished, len(self.workload))
                self.assertEqual(ops["insert"], len(self.workload))
                self.assertEqual(ops["extract"], len(self.workload))

    def test_workload_not_modified_and_reproducible(self):
        simulate(self.workload, "Priority+Aging")
        self.assertTrue(all(t.start_time is None for t in self.workload))
        self.assertTrue(all(t.priority == t.base_priority for t in self.workload))
        self.assertEqual(generate_workload(50, 0.8, 1), generate_workload(50, 0.8, 1))

    def ready_at(self, finished, task):
        """Tasks that had arrived but not started when `task` was dispatched."""
        return [t for t in finished
                if t.arrival_time <= task.start_time and t.start_time >= task.start_time]

    def test_fifo_runs_in_arrival_order(self):
        finished, _ = simulate(self.workload, "FIFO")
        arrivals = [t.arrival_time for t in finished]
        self.assertEqual(arrivals, sorted(arrivals))

    def test_priority_picks_highest_ready_task(self):
        finished, _ = simulate(self.workload, "Priority")
        for t in finished:
            ready = self.ready_at(finished, t)
            self.assertEqual(t.priority, max(r.priority for r in ready))

    def test_edf_picks_earliest_deadline(self):
        finished, _ = simulate(self.workload, "EDF")
        for t in finished:
            ready = self.ready_at(finished, t)
            self.assertEqual(t.deadline, min(r.deadline for r in ready))

    def test_aging_raises_priority_within_cap(self):
        finished, ops = simulate(self.workload, "Priority+Aging")
        self.assertGreater(ops["increase_key"], 0)
        self.assertTrue(all(t.base_priority <= t.priority <= MAX_PRIORITY for t in finished))
        self.assertTrue(any(t.priority > t.base_priority for t in finished))
        low_aged = max(t.waiting_time for t in finished if t.base_priority <= 3)
        low_plain = max(t.waiting_time for t in simulate(self.workload, "Priority")[0]
                        if t.base_priority <= 3)
        self.assertLess(low_aged, low_plain)   # aging reduces starvation

    def test_idle_gaps(self):
        tasks = [Task(0, 5, arrival_time=0, duration=2, deadline=10),
                 Task(1, 5, arrival_time=100, duration=3, deadline=110)]
        finished, _ = simulate(tasks, "Priority")
        self.assertEqual([t.start_time for t in finished], [0, 100])
        s = summarize(finished)
        self.assertEqual(s["avg_wait"], 0)
        self.assertEqual(s["deadline_miss_pct"], 0)


if __name__ == "__main__":
    unittest.main()
