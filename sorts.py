"""
Comparison sorts used as baselines for Heapsort in benchmark_sorting.py.

merge_sort            -- Cormen et al. (2022), Chapter 2 (from my Assignment 2)
randomized_quicksort  -- Cormen et al. (2022), Chapter 7, random pivot with a
                         three-way partition (from my Assignment 3)

Both return a NEW sorted list and leave the input unchanged.
"""

import random


# ---------------------------------------------------------------------------
# Merge Sort  --  T(n) = 2T(n/2) + Theta(n)  =>  Theta(n lg n) in every case
# ---------------------------------------------------------------------------

def merge_sort(A):
    """Return a new list containing the elements of A in increasing order."""
    A = list(A)
    _merge_sort(A, 0, len(A) - 1)
    return A


def _merge_sort(A, p, r):
    """Sort A[p..r] in place (indices are inclusive, as in CLRS)."""
    if p >= r:                      # zero or one element: already sorted
        return
    q = (p + r) // 2                # divide: midpoint
    _merge_sort(A, p, q)            # conquer: sort left half
    _merge_sort(A, q + 1, r)        # conquer: sort right half
    _merge(A, p, q, r)              # combine: merge the two sorted halves


def _merge(A, p, q, r):
    """Merge sorted subarrays A[p..q] and A[q+1..r] into A[p..r]."""
    L = A[p:q + 1]                  # Theta(n) auxiliary space
    R = A[q + 1:r + 1]
    i = j = 0
    k = p
    # Repeatedly copy the smaller front element back into A.
    while i < len(L) and j < len(R):
        if L[i] <= R[j]:            # <= keeps the sort stable
            A[k] = L[i]
            i += 1
        else:
            A[k] = R[j]
            j += 1
        k += 1
    # Copy whichever side still has elements left.
    while i < len(L):
        A[k] = L[i]
        i += 1
        k += 1
    while j < len(R):
        A[k] = R[j]
        j += 1
        k += 1


# ---------------------------------------------------------------------------
# Randomized Quicksort  --  expected Theta(n lg n) on every input
# ---------------------------------------------------------------------------

def randomized_quicksort(A, rng=None):
    """
    Return a new list with the elements of A in increasing order.

    The pivot is chosen uniformly at random from the subarray being
    partitioned, so no particular input (sorted, reverse-sorted, ...) can
    force the worst case.  A three-way partition groups every key equal to
    the pivot in the middle, so arrays with many repeated values are sorted
    quickly too (an all-equal array takes a single Theta(n) pass).

    rng: optional random.Random instance, for reproducible runs.
    """
    rng = rng or random
    A = list(A)                         # never modify the caller's list
    _randomized_quicksort(A, 0, len(A) - 1, rng)
    return A


def _randomized_quicksort(A, p, r, rng):
    """
    Sort A[p..r] in place (inclusive indices, as in CLRS).

    We recurse on the smaller side and loop on the larger side, so the call
    stack is O(lg n) deep no matter how unlucky the pivots are.  This only
    changes stack depth, not the running time.
    """
    while p < r:                        # 0 or 1 element: already sorted
        lt, gt = _three_way_partition(A, p, r, rng)
        # Now A[p..lt-1] < pivot, A[lt..gt] == pivot, A[gt+1..r] > pivot.
        # The middle block is in its final place and is never touched again.
        if lt - p < r - gt:
            _randomized_quicksort(A, p, lt - 1, rng)
            p = gt + 1
        else:
            _randomized_quicksort(A, gt + 1, r, rng)
            r = lt - 1


def _three_way_partition(A, p, r, rng):
    """
    Partition A[p..r] around a uniformly random pivot (Dijkstra's
    "Dutch national flag" scheme).  Returns (lt, gt) such that

        A[p..lt-1]  <  x  ==  A[lt..gt]  <  A[gt+1..r]

    Loop invariant (for the scan index i):
        A[p..lt-1]  < x      A[lt..i-1] == x
        A[gt+1..r]  > x      A[i..gt]   not yet examined
    """
    x = A[rng.randint(p, r)]            # pivot value, uniform over A[p..r]
    lt, i, gt = p, p, r
    while i <= gt:
        if A[i] < x:                    # belongs in the "less" block
            A[lt], A[i] = A[i], A[lt]
            lt += 1
            i += 1
        elif x < A[i]:                  # belongs in the "greater" block
            A[i], A[gt] = A[gt], A[i]
            gt -= 1                     # don't advance i: new A[i] is unseen
        else:                           # equal to the pivot
            i += 1
    return lt, gt
