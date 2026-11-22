import random

import pytest

from app.core.min_heap import MinHeap, top_k_largest


def test_push_pop_sorted_order():
    rnd = random.Random(7)
    data = [rnd.randint(-100, 100) for _ in range(300)]
    h = MinHeap()
    for x in data:
        h.push(x)
    assert [h.pop() for _ in range(len(data))] == sorted(data)


def test_heapify_and_peek():
    data = [9, 4, 7, 1, 8, 2, 6]
    h = MinHeap(data)
    assert h.peek() == 1 and len(h) == 7
    assert [h.pop() for _ in range(7)] == sorted(data)


def test_replace():
    h = MinHeap([5, 3, 8])
    assert h.replace(10) == 3
    assert [h.pop() for _ in range(3)] == [5, 8, 10]


def test_empty_errors():
    h = MinHeap()
    assert not h
    for fn in (h.pop, h.peek):
        with pytest.raises(IndexError):
            fn()


def test_top_k_matches_sorted():
    rnd = random.Random(3)
    data = [rnd.randint(0, 50) for _ in range(200)]
    for k in (1, 5, 50, 500):
        assert [x for x in top_k_largest(data, k)] == sorted(data, reverse=True)[:k]
    assert top_k_largest(data, 0) == []


def test_top_k_with_key_and_unorderable_items():
    items = [{"n": "a", "s": 3}, {"n": "b", "s": 9}, {"n": "c", "s": 5}]
    assert [d["n"] for d in top_k_largest(items, 2, key=lambda d: d["s"])] == ["b", "c"]
