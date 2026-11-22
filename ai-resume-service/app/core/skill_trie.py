"""
Aho-Corasick multi-pattern matcher for skill extraction.

Old approach : ~150 separate regex scans over the text  -> O(patterns * n)
This approach: build ONE automaton once, scan the text once -> O(n + matches)

How it works (good for interview explanation):
  1. Trie    : every pattern ("python", "machine learning", ...) is inserted
               into a prefix tree.
  2. Failure : for each node, a "fail" link points to the longest proper
               suffix of that node's string that is also a trie prefix.
               Built with BFS. When a character has no edge we follow fail
               links instead of restarting from the root.
  3. Output  : each node also lists every pattern that ends there (merged
               along fail links, so "she" also reports "he").
  4. Search  : walk the text char by char, report matches, then
               * keep only matches with word boundaries ("java" != "javascript")
               * resolve overlaps longest-first ("rest api" beats "api"/"rest")
"""
from __future__ import annotations

import re
from collections import Counter, deque
from dataclasses import dataclass

from .skills_db import AMBIGUOUS_PATTERNS, PATTERN_TO_CANONICAL


class AhoCorasick:
    def __init__(self, patterns: list[str]):
        self._goto: list[dict[str, int]] = [{}]
        self._fail: list[int] = [0]
        self._out: list[list[str]] = [[]]
        for p in patterns:
            self._insert(p)
        self._build()

    def _insert(self, pattern: str) -> None:
        node = 0
        for ch in pattern:
            nxt = self._goto[node].get(ch)
            if nxt is None:
                self._goto.append({})
                self._fail.append(0)
                self._out.append([])
                nxt = len(self._goto) - 1
                self._goto[node][ch] = nxt
            node = nxt
        self._out[node].append(pattern)

    def _build(self) -> None:
        queue: deque[int] = deque(self._goto[0].values())  # depth-1 nodes fail to root
        while queue:
            node = queue.popleft()
            for ch, child in self._goto[node].items():
                f = self._fail[node]
                while f and ch not in self._goto[f]:
                    f = self._fail[f]
                self._fail[child] = self._goto[f].get(ch, 0)
                if self._fail[child] == child:   # safety for depth-1
                    self._fail[child] = 0
                self._out[child] = self._out[child] + self._out[self._fail[child]]
                queue.append(child)

    def search(self, text: str) -> list[tuple[int, int, str]]:
        """Return every raw match as (start, end_exclusive, pattern)."""
        results = []
        state = 0
        for i, ch in enumerate(text):
            while state and ch not in self._goto[state]:
                state = self._fail[state]
            state = self._goto[state].get(ch, 0)
            for pat in self._out[state]:
                results.append((i - len(pat) + 1, i + 1, pat))
        return results


@dataclass(frozen=True)
class SkillMatch:
    skill: str        # canonical name
    start: int
    end: int


_LIST_LEFT = set(",/|(:;•·-–*")
_LIST_RIGHT = set(",/|);•·-–*.")


def _list_context(text: str, start: int, end: int) -> bool:
    """True if the token sits in a list-like spot: 'Languages: Python, C, Go'."""
    i = start - 1
    while i >= 0 and text[i] in " \t":
        i -= 1
    left_ok = i < 0 or text[i] == "\n" or text[i] in _LIST_LEFT
    j = end
    while j < len(text) and text[j] in " \t":
        j += 1
    right_ok = j >= len(text) or text[j] == "\n" or text[j] in _LIST_RIGHT
    return left_ok and right_ok


class SkillMatcher:
    def __init__(self, pattern_to_canonical: dict[str, str] | None = None,
                 ambiguous: frozenset[str] = AMBIGUOUS_PATTERNS):
        p2c = pattern_to_canonical or PATTERN_TO_CANONICAL
        self._p2c = p2c
        self._ambiguous = ambiguous
        self._automaton = AhoCorasick([p for p in p2c if p not in ambiguous])
        self._ambig_regex = {
            p: re.compile(r"(?<![a-z0-9+#.])" + re.escape(p) + r"(?![a-z0-9+#])", re.I)
            for p in ambiguous if p in p2c
        }

    # -- main pass (non-ambiguous patterns, on whitespace-normalised text) --------------
    def _main_pass(self, text: str) -> list[SkillMatch]:
        norm = re.sub(r"\s+", " ", text.lower())
        candidates = []
        for start, end, pat in self._automaton.search(norm):
            before_ok = start == 0 or not norm[start - 1].isalnum()
            after_ok = end == len(norm) or not norm[end].isalnum()
            if before_ok and after_ok:
                candidates.append((start, end, pat))
        # Longest-first overlap resolution ("rest api" beats "api", "c++" beats "c").
        candidates.sort(key=lambda m: (-(m[1] - m[0]), m[0]))
        occupied = bytearray(len(norm))
        chosen = []
        for start, end, pat in candidates:
            if any(occupied[start:end]):
                continue
            occupied[start:end] = b"\x01" * (end - start)
            chosen.append(SkillMatch(self._p2c[pat], start, end))
        return chosen

    # -- second pass: ambiguous tokens need list context ---------------------------------
    def _ambiguous_pass(self, text: str) -> list[SkillMatch]:
        found = []
        for pat, rx in self._ambig_regex.items():
            for m in rx.finditer(text):
                if _list_context(text, m.start(), m.end()):
                    found.append(SkillMatch(self._p2c[pat], m.start(), m.end()))
        return found

    def find(self, text: str) -> list[SkillMatch]:
        return self._main_pass(text) + self._ambiguous_pass(text)

    def count(self, text: str) -> Counter:
        """canonical skill -> number of mentions."""
        return Counter(m.skill for m in self.find(text))


# Module-level singleton: building the automaton once, at import time.
matcher = SkillMatcher()
