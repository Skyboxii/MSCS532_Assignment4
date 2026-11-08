# MSCS532 Assignment 4 – Heaps: Heapsort, Priority Queue, and Scheduler

Python implementations of Heapsort (Cormen et al., 2022, Ch. 6) and a
binary-heap priority queue of tasks (Section 6.5), a CPU-scheduling simulation
built on the queue, unit tests, benchmarks, and a full written analysis in
[REPORT.md](REPORT.md).

## Files

| File | Purpose |
|------|---------|
| `heapsort.py` | `heapsort(A)`, `heapsort_inplace(A)`, `build_max_heap(A)`, `max_heapify(A, i, heap_size)` (iterative, O(1) extra space) |
| `priority_queue.py` | `Task` dataclass and `PriorityQueue` (array-backed binary heap, max or min mode, task_id → index map) |
| `scheduler.py` | Non-preemptive single-CPU simulation comparing FIFO, Priority, Priority + aging, and EDF |
| `sorts.py` | Merge Sort (Assignment 2) and Randomized Quicksort (Assignment 3), used as baselines |
| `test_*.py` | 29 unit tests (edge cases, heap invariants after every operation, scheduler correctness) |
| `benchmark_sorting.py` | Heapsort vs. Merge Sort, Quicksort, and `sorted()`: time, comparisons, memory |
| `benchmark_priority_queue.py` | Levels moved and time per operation for queues of 1,000–256,000 tasks |
| `bench_util.py` | Turns off Windows power throttling so timings are repeatable on hybrid-core laptops |
| `results/` | Raw CSVs, console output, and charts |
| `REPORT.md` | Report: design choices, complexity analysis, empirical results, scheduling analysis |

## Priority queue API

| Operation | Cost | Notes |
|-----------|------|-------|
| `insert(task)` | O(lg n) | append as a leaf, sift up; O(1) on average for random keys |
| `extract_max()` / `extract_min()` | O(lg n) | last leaf replaces the root, sift down |
| `increase_key(task_id, k)` / `decrease_key(task_id, k)` | O(lg n) | O(1) lookup through the index map, then one sift |
| `is_empty()`, `peek()`, `len()`, `in` | O(1) | |
| `build(tasks)` | O(n) | bottom-up heapify |
| `remove(task_id)` | O(lg n) | |

`PriorityQueue(kind="max", key_attr="priority")` is the default. EDF uses
`kind="min", key_attr="deadline"`, and FIFO uses `kind="min", key_attr="arrival_time"`.
Equal keys leave in arrival order.

```python
from priority_queue import PriorityQueue, Task

pq = PriorityQueue()                       # max-heap on priority
pq.insert(Task(1, priority=3, arrival_time=0))
pq.insert(Task(2, priority=9, arrival_time=1))
pq.increase_key(1, 10)                     # task 1 is now the most urgent
pq.extract_max().task_id                   # 1
pq.is_empty()                              # False
```

## Requirements

Python 3.8+. The implementations and tests use only the standard library;
the benchmarks and scheduler charts need `matplotlib`:

```bash
pip install matplotlib
```

## Usage

```bash
python heapsort.py                   # demo (CLRS Figure 6.3 example)
python priority_queue.py             # demo of insert / key changes / extract
python -m unittest -v                # run all 29 tests
python scheduler.py                  # ~5 s; scheduling comparison + results/scheduler_*
python benchmark_priority_queue.py   # ~1 min; results/pq_*
python benchmark_sorting.py          # ~3 min; results/sorting_*
```

(On Windows with the Python launcher, use `py` in place of `python`.)

## Summary of findings

### Heapsort (n = 100,000; Windows 11, Python 3.13.9)

| Input | Heapsort | Merge Sort | Randomized Quicksort | `sorted()` |
|-------|---------:|-----------:|---------------------:|-----------:|
| Random   | 172 ms / 3,019,603 cmp | 147 ms / 1,536,206 cmp | 147 ms / 3,138,166 cmp | 11.4 ms |
| Sorted   | 160 ms / 3,112,517 cmp | 113 ms / 853,904 cmp | 131 ms / 3,131,077 cmp | 0.30 ms |
| Reverse  | 149 ms / 2,926,640 cmp | 113 ms / 815,024 cmp | 131 ms / 3,047,218 cmp | 0.34 ms |
| Repeated (10 values) | 141 ms / 2,766,786 cmp | 131 ms / 1,483,116 cmp | 16.4 ms / 519,772 cmp | 4.0 ms |
| All equal | 15.5 ms / 299,994 cmp | 112 ms / 853,904 cmp | 3.3 ms / 200,000 cmp | 0.22 ms |

- Heapsort is Θ(n lg n) on every distinct-key input. Its comparisons stayed at
  1.6–1.9 n lg n for sorted, reverse, and random input at all sizes, and its
  time per n lg n was flat. With all keys equal it is Θ(n), exactly 3n − 6
  comparisons.
- It was the slowest of the three O(n lg n) sorts. It makes about twice Merge
  Sort's comparisons, and its sift-down accesses memory less predictably than
  Quicksort's sequential scans.
- It needs O(1) extra space. Its peak memory was only the copy of the input,
  while Merge Sort needed a full second array.

### Priority queue

- Inserting a new maximum climbs the whole heap (17 levels at n = 256,000), and
  `extract_max` moves one to two levels fewer than lg n. A random-key insert
  moves only about 1.3 levels at every size.
- `build()` (O(n)) took 160 ms for 256,000 tasks, against 308 ms for 256,000
  separate inserts.

### Scheduler (5,000 tasks, load 0.9)

| Policy | Avg wait | High-priority avg wait | Low-priority max wait | Deadline misses |
|--------|---------:|-----------------------:|----------------------:|----------------:|
| FIFO | 28.9 | 28.8 | 167 | 45.9% |
| Priority | 28.5 | 4.0 | 936 | 26.2% |
| Priority + aging | 28.7 | 6.8 | 229 | 35.8% |
| EDF | 24.6 | 24.6 | 171 | 34.2% |

- Priority scheduling does not change the average wait. It moves the waiting
  from urgent tasks to low-priority ones, which starve as the load grows.
- Aging (4,451 `increase_key` calls) cut the worst low-priority wait by 4×,
  at a small cost to urgent tasks.
- EDF misses the fewest deadlines at low and moderate load (3.1% vs. 7.4% for
  FIFO at load 0.5). Near overload it degrades sharply (the domino effect).

## References

Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022).
*Introduction to Algorithms* (4th ed.). MIT Press.

Liu, C. L., & Layland, J. W. (1973). Scheduling algorithms for
multiprogramming in a hard-real-time environment. *Journal of the ACM, 20*(1), 46–61.

Schaffer, R., & Sedgewick, R. (1993). The analysis of heapsort.
*Journal of Algorithms, 15*(1), 76–100.

Williams, J. W. J. (1964). Algorithm 232: Heapsort.
*Communications of the ACM, 7*(6), 347–348.
