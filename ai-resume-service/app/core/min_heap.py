"""
Min-heap written from scratch (array-based binary heap), plus a top-K helper.

Array layout:  parent(i) = (i-1)//2   left(i) = 2i+1   right(i) = 2i+2
Invariant   :  every parent <= both children, so the smallest item is at index 0.

  push       O(log n)   append at the end, sift UP
  pop        O(log n)   swap root with last, remove, sift DOWN
  peek       O(1)
  replace    O(log n)   pop + push in one sift (used by top-K)
  heapify    O(n)       build from a list by sifting down from the last parent

Where it is used in this project
  * top_k_largest : rank the best K roles for a student without sorting everything.
                    Keep a min-heap of size K; the root is the weakest of the current
                    top K, so a new item only has to beat the root.   O(n log k)
  * learning_order: "which skill is ready AND most important" (core/skill_graph.py).
"""
from __future__ import annotations

from typing import Any, Callable, Iterable


class MinHeap:
    def __init__(self, items: Iterable[Any] | None = None):
        self._a: list[Any] = list(items) if items else []
        for i in range(len(self._a) // 2 - 1, -1, -1):      # O(n) heapify
            self._sift_down(i)

    def __len__(self) -> int:
        return len(self._a)

    def __bool__(self) -> bool:
        return bool(self._a)

    def peek(self) -> Any:
        if not self._a:
            raise IndexError("peek from empty heap")
        return self._a[0]

    def push(self, item: Any) -> None:
        self._a.append(item)
        self._sift_up(len(self._a) - 1)

    def pop(self) -> Any:
        if not self._a:
            raise IndexError("pop from empty heap")
        top, last = self._a[0], self._a.pop()
        if self._a:
            self._a[0] = last
            self._sift_down(0)
        return top

    def replace(self, item: Any) -> Any:
        """Pop the smallest and push `item` with a single sift-down."""
        if not self._a:
            raise IndexError("replace on empty heap")
        top = self._a[0]
        self._a[0] = item
        self._sift_down(0)
        return top

    # -- internals ---------------------------------------------------------------
    def _sift_up(self, i: int) -> None:
        a = self._a
        item = a[i]
        while i > 0:
            parent = (i - 1) // 2
            if a[parent] <= item:
                break
            a[i] = a[parent]
            i = parent
        a[i] = item

    def _sift_down(self, i: int) -> None:
        a, n = self._a, len(self._a)
        item = a[i]
        while True:
            child = 2 * i + 1
            if child >= n:
                break
            if child + 1 < n and a[child + 1] < a[child]:     # pick the smaller child
                child += 1
            if item <= a[child]:
                break
            a[i] = a[child]
            i = child
        a[i] = item


def top_k_largest(items: Iterable[Any], k: int, key: Callable[[Any], Any] = lambda x: x) -> list[Any]:
    """K largest items by `key`, best first, using a size-K min-heap. O(n log k)."""
    if k <= 0:
        return []
    heap = MinHeap()
    for idx, item in enumerate(items):
        entry = (key(item), idx, item)          # idx breaks ties so items are never compared
        if len(heap) < k:
            heap.push(entry)
        elif entry[:2] > heap.peek()[:2]:       # beats the weakest of the current top K
            heap.replace(entry)
    result = []
    while heap:
        result.append(heap.pop()[2])            # pops weakest first ...
    result.reverse()                            # ... so flip to best first
    return result
