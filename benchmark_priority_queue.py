"""
Benchmark the heap-based PriorityQueue operations as the queue grows.

For heap sizes n = 1,000 ... 256,000 it measures, per operation:
  * insert with a random key, and insert of a new maximum (worst case:
    the new task sifts all the way to the root),
  * extract_max,
  * increase_key on a random queued task,
  * building the queue with build() (O(n)) versus n inserts (O(n lg n)).
It records both time and the number of swaps (levels moved), which is the
machine-independent measure of the O(lg n) work.

Writes results/pq_*.csv and results/pq_*.png.

Usage:  py benchmark_priority_queue.py      (about 1 minute)
"""

import csv
import math
import os
import random
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bench_util import stabilize_timing
from priority_queue import PriorityQueue, Task

SIZES = [1000, 4000, 16000, 64000, 256000]
OPS = 2000                   # operations timed at each size
SEED = 532
OUT_DIR = "results"


class CountingPQ(PriorityQueue):
    """PriorityQueue that counts swaps (each swap = one level of a sift)."""

    def __init__(self, *a, **kw):
        self.swaps = 0
        super().__init__(*a, **kw)

    def _swap(self, i, j):
        self.swaps += 1
        super()._swap(i, j)


def make_tasks(n, rng, start_id=0):
    return [Task(start_id + i, rng.random(), arrival_time=start_id + i) for i in range(n)]


def measure(pq, fn, args_list):
    """Average microseconds and swaps per call of fn over args_list."""
    pq.swaps = 0
    start = time.perf_counter()
    for args in args_list:
        fn(*args)
    elapsed = time.perf_counter() - start
    return elapsed / len(args_list) * 1e6, pq.swaps / len(args_list)


def run():
    rows = []
    for n in SIZES:
        rng = random.Random(SEED + n)
        tasks = make_tasks(n, rng)

        # Build: O(n) heapify vs. n inserts.
        pq = CountingPQ()
        start = time.perf_counter()
        pq.build(tasks)
        build_ms = (time.perf_counter() - start) * 1000
        build_swaps = pq.swaps
        pq2 = CountingPQ()
        start = time.perf_counter()
        for t in make_tasks(n, random.Random(SEED + n)):
            pq2.insert(t)
        inserts_ms = (time.perf_counter() - start) * 1000

        # Insert with a random key (queue size stays about n), then remove again.
        new = make_tasks(OPS, rng, start_id=n)
        ins_us, ins_sw = measure(pq, pq.insert, [(t,) for t in new])
        for t in new:
            pq.remove(t.task_id)

        # Insert a new maximum each time: worst case, sifts to the root.
        top = [Task(n + OPS + i, 2.0 + i, arrival_time=0) for i in range(OPS)]
        worst_us, worst_sw = measure(pq, pq.insert, [(t,) for t in top])

        # Extract max (removes the OPS maxima just added, queue back to size n).
        ext_us, ext_sw = measure(pq, pq.extract_max, [()] * OPS)

        # Increase key of random queued tasks by a random amount.
        # (new keys are computed inside the loop so repeated ids stay valid)
        ids = [rng.randrange(n) for _ in range(OPS)]
        bumps = [rng.random() for _ in range(OPS)]

        def bump(tid, delta):
            pq.increase_key(tid, pq.get(tid).priority + delta)
        inc_us, inc_sw = measure(pq, bump, list(zip(ids, bumps)))

        pq.check_invariants()
        rows.append({"n": n, "lg_n": round(math.log2(n), 2),
                     "insert_random_us": round(ins_us, 3), "insert_random_swaps": round(ins_sw, 2),
                     "insert_max_us": round(worst_us, 3), "insert_max_swaps": round(worst_sw, 2),
                     "extract_max_us": round(ext_us, 3), "extract_max_swaps": round(ext_sw, 2),
                     "increase_key_us": round(inc_us, 3), "increase_key_swaps": round(inc_sw, 2),
                     "build_ms": round(build_ms, 2), "build_swaps_per_task": round(build_swaps / n, 3),
                     "n_inserts_ms": round(inserts_ms, 2)})
        r = rows[-1]
        print("n={:>7} lg n={:>5}  insert {:.2f} us ({} swaps)  insert-max {:.2f} us ({} swaps)  "
              "extract {:.2f} us ({} swaps)  increase-key {:.2f} us ({} swaps)  "
              "build {} ms vs inserts {} ms".format(
                  n, r["lg_n"], ins_us, r["insert_random_swaps"], worst_us, r["insert_max_swaps"],
                  ext_us, r["extract_max_swaps"], inc_us, r["increase_key_swaps"],
                  r["build_ms"], r["n_inserts_ms"]), flush=True)
    return rows


def plot(rows):
    ns = [r["n"] for r in rows]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    series = [("insert_random", "insert (random key)", "o-"),
              ("insert_max", "insert (new maximum)", "s-"),
              ("extract_max", "extract_max", "^-"),
              ("increase_key", "increase_key (random)", "d-")]
    for key, label, style in series:
        ax1.plot(ns, [r[key + "_swaps"] for r in rows], style, label=label)
        ax2.plot(ns, [r[key + "_us"] for r in rows], style, label=label)
    ax1.plot(ns, [math.log2(n) for n in ns], "k:", label="lg n")
    ax1.set_ylabel("swaps (levels moved) per operation")
    ax1.set_title("Heap levels moved per operation")
    ax2.set_ylabel("µs per operation")
    ax2.set_title("Time per operation")
    for ax in (ax1, ax2):
        ax.set_xscale("log")
        ax.set_xlabel("tasks in the queue n (log scale)")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "pq_operations.png"), dpi=150)
    plt.close(fig)


def main():
    print("power throttling disabled:", stabilize_timing())
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = run()
    with open(os.path.join(OUT_DIR, "pq_operations.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    plot(rows)
    print("Results written to", OUT_DIR)


if __name__ == "__main__":
    main()
