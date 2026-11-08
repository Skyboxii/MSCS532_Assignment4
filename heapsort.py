"""
Heapsort.

Follows Cormen, Leiserson, Rivest, & Stein, Introduction to Algorithms
(4th ed.), Chapter 6 (Heapsort): MAX-HEAPIFY (6.2), BUILD-MAX-HEAP (6.3),
and HEAPSORT (6.4).  CLRS indexes arrays from 1; Python lists start at 0,
so for a node at index i:

    parent(i) = (i - 1) // 2      left(i) = 2i + 1      right(i) = 2i + 2

Running time: Theta(n lg n) in the worst case (and for distinct keys in the
best and average cases too).  Extra space: O(1) -- the heap lives inside the
array being sorted and MAX-HEAPIFY is written as a loop, not recursion.
"""


def heapsort(A):
    """Return a new list with the elements of A in increasing order."""
    A = list(A)                    # leave the caller's list untouched
    heapsort_inplace(A)
    return A


def heapsort_inplace(A):
    """
    Sort list A in place in increasing order (CLRS HEAPSORT).

    Phase 1: turn A into a max-heap, so the largest key is at A[0].
    Phase 2: repeatedly swap the root (current maximum) with the last
             element of the heap, shrink the heap by one, and restore the
             heap property at the root.  The sorted suffix A[heap_size..n-1]
             grows from the right.
    """
    build_max_heap(A)
    for heap_size in range(len(A) - 1, 0, -1):
        A[0], A[heap_size] = A[heap_size], A[0]   # move max to its final slot
        max_heapify(A, 0, heap_size)              # heap is now A[0..heap_size-1]


def build_max_heap(A):
    """
    Rearrange A into a max-heap in O(n) time (CLRS BUILD-MAX-HEAP).

    Nodes A[n//2 .. n-1] are leaves, which are already 1-element heaps, so
    we heapify the internal nodes from the bottom up.  Loop invariant: at the
    start of each iteration, every node i+1, i+2, ..., n-1 is the root of a
    max-heap.
    """
    n = len(A)
    for i in range(n // 2 - 1, -1, -1):
        max_heapify(A, i, n)


def max_heapify(A, i, heap_size):
    """
    Let the key at A[i] float down so the subtree rooted at i becomes a
    max-heap (CLRS MAX-HEAPIFY).  Assumes the subtrees rooted at left(i) and
    right(i) are already max-heaps.  Only A[0..heap_size-1] is the heap.

    Each loop iteration moves one level down the tree, so the cost is
    O(h) = O(lg n), where h is the height of node i.  An iterative loop is
    used instead of CLRS's tail recursion so the extra space is O(1).
    """
    while True:
        left = 2 * i + 1
        right = left + 1
        largest = i
        if left < heap_size and A[largest] < A[left]:
            largest = left
        if right < heap_size and A[largest] < A[right]:
            largest = right
        if largest == i:           # A[i] is >= both children: done
            return
        A[i], A[largest] = A[largest], A[i]
        i = largest                # continue sifting down from the child


def is_max_heap(A, heap_size=None):
    """True if A[0..heap_size-1] satisfies the max-heap property."""
    n = len(A) if heap_size is None else heap_size
    return all(not (A[(i - 1) // 2] < A[i]) for i in range(1, n))


if __name__ == "__main__":
    data = [4, 1, 3, 2, 16, 9, 10, 14, 8, 7]          # CLRS Figure 6.3 input
    heap = list(data)
    build_max_heap(heap)
    print("Input:          ", data)
    print("After build-heap:", heap)
    print("Heapsort:       ", heapsort(data))
