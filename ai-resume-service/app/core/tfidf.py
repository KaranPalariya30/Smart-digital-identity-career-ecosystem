"""
TF-IDF from scratch.

v1 problem: IDF was computed over just 2 documents (the resume and the JD),
so almost every word got the same weight and IDF did very little.
v2 fix    : IDF can come from a corpus (many JDs / resumes). Build it once with
            scripts/build_idf.py -> data/idf_corpus.json. If that file is absent
            we fall back to the old pair-only IDF so nothing breaks.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

from ..config import settings


def compute_tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens)
    return {w: c / total for w, c in counts.items()}


def smoothed_idf(n_docs: int, df: int) -> float:
    return math.log((n_docs + 1) / (df + 1)) + 1


def compute_idf(all_documents_tokens: list[list[str]]) -> dict[str, float]:
    n = len(all_documents_tokens)
    df: dict[str, int] = {}
    for doc in all_documents_tokens:
        for w in set(doc):
            df[w] = df.get(w, 0) + 1
    return {w: smoothed_idf(n, d) for w, d in df.items()}


class CorpusIdf:
    """Document frequencies learned from a corpus."""

    def __init__(self, n_docs: int, df: dict[str, int]):
        self.n_docs = n_docs
        self.df = df

    def idf(self, word: str) -> float:
        return smoothed_idf(self.n_docs, self.df.get(word, 0))

    @classmethod
    def from_documents(cls, docs_tokens: list[list[str]]) -> "CorpusIdf":
        df: dict[str, int] = {}
        for doc in docs_tokens:
            for w in set(doc):
                df[w] = df.get(w, 0) + 1
        return cls(len(docs_tokens), df)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"n_docs": self.n_docs, "df": self.df}), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CorpusIdf":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(raw["n_docs"], raw["df"])


@lru_cache(maxsize=1)
def get_corpus_idf() -> CorpusIdf | None:
    path = Path(settings.idf_path)
    return CorpusIdf.load(path) if path.exists() else None


def compute_tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    return {w: tf * idf.get(w, 1.0) for w, tf in compute_tf(tokens).items()}


def build_tfidf_for_pair(resume_tokens: list[str], jd_tokens: list[str],
                         corpus: CorpusIdf | None = None):
    if corpus is not None:
        vocab = set(resume_tokens) | set(jd_tokens)
        idf = {w: corpus.idf(w) for w in vocab}
    else:
        idf = compute_idf([resume_tokens, jd_tokens])
    return compute_tfidf_vector(resume_tokens, idf), compute_tfidf_vector(jd_tokens, idf)


def get_top_keywords(vec: dict[str, float], top_n: int = 15) -> list[tuple[str, float]]:
    filtered = {w: s for w, s in vec.items() if "_" not in w}
    return sorted(filtered.items(), key=lambda p: p[1], reverse=True)[:top_n]
