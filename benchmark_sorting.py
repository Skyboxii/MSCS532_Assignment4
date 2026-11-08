"""
Benchmark Heapsort against Merge Sort, Randomized Quicksort, and Python's
built-in sorted() (Timsort) on random, sorted, reverse-sorted, repeated, and
all-equal arrays.

Records best-of-N wall-clock time (time.perf_counter), key comparisons
(machine-independent), and peak memory (tracemalloc).  Writes
results/sorting_*.csv and results/sorting_*.png.

Usage:  py benchmark_sorting.py      (about 3 minutes)
"""

import csv
import math
import os
import random
import time
import tracemalloc

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bench_util import stabilize_timing
from heapsort import heapsort
from sorts import merge_sort, randomized_quicksort

SIZES = [1000, 5000, 10000, 25000, 50000, 100000]
REPEATS = 5
TIME_BUDGET = 3.0
SEED = 532
OUT_DIR = "results"

ALGORITHMS = {
    "Heapsort": heapsort,
    "Merge Sort": merge_sort,
    "Randomized Quicksort": lambda A: randomized_quicksort(A, rng=random.Random(SEED)),
    "Python sorted()": sorted,
}
STYLES = {"Heapsort": "o-", "Merge Sort": "s-", "Randomized Quicksort": "^-",
          "Python sorted()": "x:"}


def repeated(n, distinct=10):
    rng = random.Random(SEED + n)
    return [rng.randrange(distinct) for _ in range(n)]


DATASETS = {
    "random": lambda n: random.Random(SEED + n).sample(range(n * 10), n),
    "sorted": lambda n: list(range(n)),
    "reverse": lambda n: list(range(n, 0, -1)),
    "repeated": repeated,
    "all equal": lambda n: [7] * n,
}


def best_time(sort, data):
    best, spent = float("inf"), 0.0
    for _ in range(REPEATS):
        copy = list(data)
        start = time.perf_counter()
        sort(copy)
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
        spent += elapsed
        if spent > TIME_BUDGET:
            break
    return best


class Counted:
    """Wraps a value and counts every comparison made against it."""
    count = 0
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        Counted.count += 1
        return self.v < other.v

    def __le__(self, other):
        Counted.count += 1
        return self.v <= other.v


def comparisons(sort, data):
    wrapped = [Counted(v) for v in data]
    Counted.count = 0
    result = sort(wrapped)
    assert [w.v for w in result] == sorted(data)
    return Counted.count


def peak_memory(sort, data):
    """Peak bytes allocated while sorting, beyond the input itself."""
    copy = list(data)
    tracemalloc.start()
    sort(copy)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def run():
    rows = []
    for dname, make in DATASETS.items():
        for n in SIZES:
            data = make(n)
            for aname, sort in ALGORITHMS.items():
                t = best_time(sort, data)
                c = comparisons(sort, data) if aname != "Python sorted()" else ""
                nlgn = n * math.log2(n)
                rows.append({"algorithm": aname, "dataset": dname, "n": n,
                             "time_ms": round(t * 1000, 3), "comparisons": c,
                             "cmp_per_nlgn": round(c / nlgn, 3) if c != "" else "",
                             "ns_per_nlgn": round(t * 1e9 / nlgn, 2)})
                print("{:<10} n={:>7}  {:<22} {:>9.2f} ms {:>12} cmp".format(
                    dname, n, aname, t * 1000, "{:,}".format(c) if c != "" else "-"),
                    flush=True)
    return rows


def run_memory(n=100000):
    rows = []
    data = DATASETS["random"](n)
    for aname, sort in ALGORITHMS.items():
        peak = peak_memory(sort, data)
        rows.append({"algorithm": aname, "n": n, "peak_bytes": peak,
                     "extra_bytes_over_copy": peak - 8 * n - 56,
                     "bytes_per_element": round(peak / n, 2)})
        print("memory {:<22} peak {:>11,} bytes".format(aname, peak), flush=True)
    return rows


def write_csv(name, rows):
    with open(os.path.join(OUT_DIR, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plot_grid(rows, metric, ylabel, filename, title, algorithms, logy=True):
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), sharex=True)
    for ax, dname in zip(axes.flat, DATASETS):
        for aname in algorithms:
            pts = [r for r in rows if r["dataset"] == dname and r["algorithm"] == aname
                   and r[metric] != ""]
            ax.plot([r["n"] for r in pts], [float(r[metric]) for r in pts], STYLES[aname],
                    label=aname, markersize=4)
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_title(dname)
        ax.set_xlabel("n")
        ax.grid(True, which="both", alpha=0.3)
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc="center", fontsize=11)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close(fig)


def plot_memory(mem):
    fig, ax = plt.subplots(figsize=(7, 4))
    names = [r["algorithm"] for r in mem]
    ax.bar(names, [r["peak_bytes"] / 1024 for r in mem], color=["tab:blue", "tab:orange",
                                                                 "tab:green", "tab:gray"])
    ax.axhline(8 * mem[0]["n"] / 1024, color="k", ls=":", label="size of the output list (8n bytes)")
    ax.set_ylabel("peak KiB while sorting")
    ax.set_title("Peak memory, n = 100,000 random keys")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "sorting_memory.png"), dpi=150)
    plt.close(fig)


def main():
    print("power throttling disabled:", stabilize_timing())
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = run()
    write_csv("sorting_results.csv", rows)
    algs = list(ALGORITHMS)
    plot_grid(rows, "time_ms", "time (ms, log scale)", "sorting_time.png",
              "Running time vs. input size (best of {} runs)".format(REPEATS), algs)
    plot_grid(rows, "cmp_per_nlgn", "comparisons / (n lg n)", "sorting_comparisons.png",
              "Key comparisons normalized by n lg n", algs[:3], logy=False)
    plot_grid(rows, "ns_per_nlgn", "ns / (n lg n)", "sorting_normalized_time.png",
              "Running time normalized by n lg n", algs, logy=False)
    mem = run_memory()
    write_csv("sorting_memory.csv", mem)
    plot_memory(mem)
    print("Results written to", OUT_DIR)


if __name__ == "__main__":
    main()
