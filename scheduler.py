"""
Task-scheduler simulation built on the heap-based PriorityQueue.

Model
-----
A single CPU runs one task at a time, non-preemptively: once a task starts it
runs for its full duration.  Tasks arrive over time (a Poisson process), each
with a priority from 1 (low) to 10 (high), a duration of 1-9 time units, and
an absolute deadline.  Whenever the CPU becomes free, every task that has
arrived is in the ready queue and the scheduler extracts the next one.

Policies (all use the same PriorityQueue class, configured differently)
----------------------------------------------------------------------
    FIFO          min-heap on arrival_time   -> first come, first served
    Priority      max-heap on priority       -> most urgent task first
    Priority+Aging  max-heap on priority, but at every dispatch each waiting
                  task's priority is raised by 1 for every AGING_INTERVAL time
                  units it has waited (capped at 10) using increase_key().
                  This prevents low-priority tasks from starving.
    EDF           min-heap on deadline       -> earliest deadline first

Usage:  py scheduler.py      (prints the comparison; writes results/scheduler_*.csv/.png)
"""

import csv
import math
import os
import random
import statistics
from dataclasses import replace

from priority_queue import PriorityQueue, Task

MAX_PRIORITY = 10
AGING_INTERVAL = 25.0            # +1 priority per 25 time units of waiting
MEAN_DURATION = 5.0              # durations are uniform integers 1..9

POLICIES = {
    "FIFO": dict(kind="min", key_attr="arrival_time", aging=False),
    "Priority": dict(kind="max", key_attr="priority", aging=False),
    "Priority+Aging": dict(kind="max", key_attr="priority", aging=True),
    "EDF": dict(kind="min", key_attr="deadline", aging=False),
}

CLASSES = [("low (1-3)", 1, 3), ("medium (4-7)", 4, 7), ("high (8-10)", 8, 10)]


def generate_workload(n=5000, load=0.9, seed=532):
    """
    n tasks with Poisson arrivals.  load = (arrival rate) x (mean duration)
    is the fraction of time the CPU would need to be busy; load >= 1 means
    work arrives faster than it can be done and the queue keeps growing.
    """
    rng = random.Random(seed)
    rate = load / MEAN_DURATION
    t = 0.0
    tasks = []
    for tid in range(n):
        t += rng.expovariate(rate)
        duration = rng.randint(1, 9)
        slack = rng.uniform(2.0, 10.0)           # deadline = arrival + slack x duration
        tasks.append(Task(task_id=tid, priority=rng.randint(1, MAX_PRIORITY),
                          arrival_time=round(t, 3), duration=duration,
                          deadline=round(t + slack * duration, 3)))
    return tasks


def simulate(workload, policy):
    """
    Run one policy on (a copy of) the workload.  Returns (finished_tasks,
    op_counts) where op_counts tallies the priority-queue operations used.
    """
    cfg = POLICIES[policy]
    tasks = sorted((replace(t) for t in workload), key=lambda t: t.arrival_time)
    pq = PriorityQueue(kind=cfg["kind"], key_attr=cfg["key_attr"])
    ops = {"insert": 0, "extract": 0, "increase_key": 0, "max_queue": 0}
    finished = []
    clock = 0.0
    i, n = 0, len(tasks)

    while i < n or not pq.is_empty():
        if pq.is_empty() and tasks[i].arrival_time > clock:
            clock = tasks[i].arrival_time          # CPU idles until next arrival
        while i < n and tasks[i].arrival_time <= clock:
            pq.insert(tasks[i])                    # O(lg q)
            ops["insert"] += 1
            i += 1
        ops["max_queue"] = max(ops["max_queue"], len(pq))

        if cfg["aging"]:
            ops["increase_key"] += apply_aging(pq, clock)

        task = pq.extract()                        # O(lg q)
        ops["extract"] += 1
        task.start_time = clock
        clock += task.duration                     # non-preemptive run
        task.finish_time = clock
        finished.append(task)
    return finished, ops


def apply_aging(pq, now):
    """
    Raise the priority of every waiting task to
        min(MAX_PRIORITY, base_priority + floor(wait / AGING_INTERVAL))
    with increase_key (O(lg q) each).  Returns how many keys changed.
    """
    changed = 0
    for task in pq.tasks():
        if task.priority >= MAX_PRIORITY:
            continue
        aged = min(MAX_PRIORITY,
                   task.base_priority + math.floor((now - task.arrival_time) / AGING_INTERVAL))
        if aged > task.priority:
            pq.increase_key(task.task_id, aged)
            changed += 1
    return changed


def percentile(values, p):
    s = sorted(values)
    k = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
    return s[k]


def summarize(finished):
    waits = [t.waiting_time for t in finished]
    turns = [t.turnaround_time for t in finished]
    makespan = max(t.finish_time for t in finished) - min(t.arrival_time for t in finished)
    out = {
        "avg_wait": statistics.mean(waits),
        "p95_wait": percentile(waits, 95),
        "max_wait": max(waits),
        "avg_turnaround": statistics.mean(turns),
        "deadline_miss_pct": 100.0 * sum(t.missed_deadline for t in finished) / len(finished),
        "throughput": len(finished) / makespan,
    }
    for label, lo, hi in CLASSES:
        group = [t for t in finished if lo <= t.base_priority <= hi]
        if not group:                          # no tasks in this class
            for key in ("avg_wait ", "max_wait ", "miss_pct "):
                out[key + label] = float("nan")
            continue
        w = [t.waiting_time for t in group]
        out["avg_wait " + label] = statistics.mean(w)
        out["max_wait " + label] = max(w)
        out["miss_pct " + label] = 100.0 * sum(t.missed_deadline for t in group) / len(group)
    return out


def main_experiment(n=5000, load=0.9, seed=532):
    workload = generate_workload(n, load, seed)
    rows = []
    for policy in POLICIES:
        finished, ops = simulate(workload, policy)
        s = summarize(finished)
        row = {"policy": policy}
        row.update({k: round(v, 2) for k, v in s.items()})
        row.update({"pq_" + k: v for k, v in ops.items()})
        rows.append(row)
    return rows


def load_sweep(loads=(0.5, 0.7, 0.8, 0.9, 1.0, 1.1), n=3000, seeds=(1, 2, 3)):
    rows = []
    for load in loads:
        for policy in POLICIES:
            acc = []
            for seed in seeds:
                finished, _ = simulate(generate_workload(n, load, seed), policy)
                acc.append(summarize(finished))
            row = {"load": load, "policy": policy}
            for key in ("avg_wait", "deadline_miss_pct", "max_wait low (1-3)",
                        "avg_wait high (8-10)"):
                row[key] = round(statistics.mean(a[key] for a in acc), 2)
            rows.append(row)
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plot(main_rows, sweep_rows, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [c[0] for c in CLASSES]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    width = 0.2
    for k, row in enumerate(main_rows):
        xs = [x + (k - 1.5) * width for x in range(len(labels))]
        ax1.bar(xs, [row["avg_wait " + c] for c in labels], width, label=row["policy"])
        ax2.bar(xs, [row["max_wait " + c] for c in labels], width, label=row["policy"])
    for ax, title in ((ax1, "Average waiting time by priority class"),
                      (ax2, "Maximum waiting time by priority class")):
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylabel("time units")
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.3)
    ax1.legend()
    fig.suptitle("Scheduler comparison, 5,000 tasks at load 0.9")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "scheduler_wait_by_class.png"), dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
    metrics = [("deadline_miss_pct", "Deadline misses (%)"),
               ("avg_wait high (8-10)", "Avg wait, high priority (time units)"),
               ("max_wait low (1-3)", "Max wait, low priority (time units, log)")]
    for ax, (key, title) in zip(axes, metrics):
        for policy in POLICIES:
            pts = [r for r in sweep_rows if r["policy"] == policy]
            ax.plot([r["load"] for r in pts], [r[key] for r in pts], "o-", label=policy)
        ax.set_xlabel("offered load ρ")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        if key.startswith("max_wait"):
            ax.set_yscale("log")
    axes[0].legend()
    fig.suptitle("Scheduling policies versus load (3,000 tasks, mean of 3 seeds)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "scheduler_load_sweep.png"), dpi=150)
    plt.close(fig)


def main():
    out_dir = "results"
    os.makedirs(out_dir, exist_ok=True)
    rows = main_experiment()
    write_csv(os.path.join(out_dir, "scheduler_summary.csv"), rows)
    print("5,000 tasks, load 0.9 (times in time units)")
    print("{:<15}{:>9}{:>9}{:>10}{:>9}{:>11}{:>12}{:>12}".format(
        "policy", "avg wait", "p95", "max wait", "miss %", "low max", "high avg", "incr_keys"))
    for r in rows:
        print("{:<15}{:>9.1f}{:>9.1f}{:>10.1f}{:>9.1f}{:>11.1f}{:>12.1f}{:>12}".format(
            r["policy"], r["avg_wait"], r["p95_wait"], r["max_wait"], r["deadline_miss_pct"],
            r["max_wait low (1-3)"], r["avg_wait high (8-10)"], r["pq_increase_key"]))
    sweep = load_sweep()
    write_csv(os.path.join(out_dir, "scheduler_load_sweep.csv"), sweep)
    plot(rows, sweep, out_dir)
    print("Results written to", out_dir)


if __name__ == "__main__":
    main()
