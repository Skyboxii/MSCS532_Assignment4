import random
import unittest

from heapsort import build_max_heap, heapsort, heapsort_inplace, is_max_heap, max_heapify


class TestHeapsort(unittest.TestCase):
    def check(self, data):
        with self.subTest(data=data[:10]):
            self.assertEqual(heapsort(data), sorted(data))

    def test_empty_and_tiny(self):
        self.check([])
        self.check([1])
        self.check([2, 1])
        self.check([1, 2])

    def test_duplicates(self):
        self.check([5] * 40)
        self.check([3, 1, 3, 2, 1, 3, 2, 2, 1])
        self.check([random.randint(0, 3) for _ in range(300)])

    def test_sorted_and_reverse(self):
        self.check(list(range(1000)))
        self.check(list(range(1000, 0, -1)))

    def test_mixed_types(self):
        self.check([-3, 2.5, 0, -1.5, 7, -3])
        self.check(["pear", "apple", "fig", "apple", "kiwi"])

    def test_random_fuzz(self):
        for _ in range(200):
            n = random.randint(0, 150)
            self.check([random.randint(-50, 50) for _ in range(n)])

    def test_input_not_modified(self):
        data = [3, 1, 2]
        heapsort(data)
        self.assertEqual(data, [3, 1, 2])

    def test_inplace(self):
        data = [9, 4, 7, 1]
        self.assertIsNone(heapsort_inplace(data))
        self.assertEqual(data, [1, 4, 7, 9])

    def test_clrs_example(self):
        # CLRS Figure 6.3: BUILD-MAX-HEAP on this array gives this heap.
        A = [4, 1, 3, 2, 16, 9, 10, 14, 8, 7]
        build_max_heap(A)
        self.assertEqual(A, [16, 14, 10, 8, 7, 9, 3, 2, 4, 1])

    def test_build_max_heap_property(self):
        for _ in range(100):
            A = [random.randint(0, 100) for _ in range(random.randint(0, 100))]
            build_max_heap(A)
            self.assertTrue(is_max_heap(A))

    def test_max_heapify_single_violation(self):
        # CLRS Figure 6.2: only the root of the subtree at index 1 is out of place.
        A = [16, 4, 10, 14, 7, 9, 3, 2, 8, 1]
        max_heapify(A, 1, len(A))
        self.assertEqual(A, [16, 14, 10, 8, 7, 9, 3, 2, 4, 1])


if __name__ == "__main__":
    unittest.main()
