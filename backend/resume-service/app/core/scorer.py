"""
Scoring: cosine similarity + keyword coverage (text side) and weighted skill
coverage (skill side), combined with weights from config.py.

v1 -> v2 changes
  * overall score no longer uses the arbitrary `* 250`; cosine is divided by a
    documented ceiling (settings.cosine_ceiling) that you can re-fit later.
  * skills now carry weights (required vs preferred, or mention frequency).
"""
import math

from ..config import settings
from .text_cleaner import preprocess
from .tfidf import build_tfidf_for_pair, get_corpus_idf, get_top_keywords


def dot_product(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):          # iterate over the smaller dict
        a, b = b, a
    return sum(v * b.get(w, 0.0) for w, v in a.items())


def vector_magnitude(v: dict[str, float]) -> float:
    return math.sqrt(sum(x * x for x in v.values()))


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    ma, mb = vector_magnitude(a), vector_magnitude(b)
    if ma == 0 or mb == 0:
        return 0.0
    return max(0.0, min(1.0, dot_product(a, b) / (ma * mb)))


def keyword_coverage(resume_tokens: list[str], jd_tokens: list[str]) -> float:
    jd_set = set(jd_tokens)
    return len(jd_set & set(resume_tokens)) / len(jd_set) if jd_set else 0.0


def _display_ok(word: str) -> bool:
    return len(word) > 3 and "_" not in word


def matched_keywords(resume_tokens, jd_tokens, limit=20) -> list[str]:
    return sorted(w for w in set(resume_tokens) & set(jd_tokens) if _display_ok(w))[:limit]


def missing_keywords(resume_tokens, jd_tokens, jd_vector, top_n=10) -> list[str]:
    missing = [(w, jd_vector.get(w, 0.0)) for w in set(jd_tokens) - set(resume_tokens) if _display_ok(w)]
    missing.sort(key=lambda x: x[1], reverse=True)
    return [w for w, _ in missing[:top_n]]


def text_similarity(resume_text: str, jd_text: str) -> dict:
    """The text half of the score (cosine + keyword coverage)."""
    r_tokens, j_tokens = preprocess(resume_text), preprocess(jd_text)
    r_vec, j_vec = build_tfidf_for_pair(r_tokens, j_tokens, get_corpus_idf())

    cosine = cosine_similarity(r_vec, j_vec)
    coverage = keyword_coverage(r_tokens, j_tokens)
    cosine_scaled = min(1.0, cosine / settings.cosine_ceiling)
    text_score = (settings.w_cosine_in_text * cosine_scaled
                  + settings.w_coverage_in_text * coverage)
    return {
        "cosine": cosine,
        "coverage": coverage,
        "text_score": text_score,
        "matched_keywords": matched_keywords(r_tokens, j_tokens),
        "missing_keywords": missing_keywords(r_tokens, j_tokens, j_vec),
        "resume_top": [w for w, _ in get_top_keywords(r_vec, 10)],
        "jd_top": [w for w, _ in get_top_keywords(j_vec, 10)],
    }


def weighted_skill_score(resume_skills: set[str], skill_weights: dict[str, float]) -> float:
    """sum(weight of skills the resume has) / sum(all weights)  ->  0..1"""
    total = sum(skill_weights.values())
    if total == 0:
        return 0.0
    got = sum(w for s, w in skill_weights.items() if s in resume_skills)
    return got / total


def combine(skill_score: float, text_score: float, has_skills: bool) -> float:
    if not has_skills:                       # JD mentioned no known skills -> text only
        return text_score
    return settings.w_skill * skill_score + settings.w_text * text_score


def score_to_grade(score: int) -> str:
    for cutoff, grade in [(90, "A+"), (80, "A"), (70, "B+"), (60, "B"),
                          (50, "C+"), (40, "C"), (30, "D")]:
        if score >= cutoff:
            return grade
    return "F"


def summary_line(score: int, matched: int, missing: int) -> str:
    if score >= 80:
        return f"Excellent match. Your resume aligns strongly with this role ({matched} skills matched)."
    if score >= 60:
        return f"Good match. You cover most requirements but {missing} important skills are missing."
    if score >= 40:
        return f"Moderate match. Consider adding {missing} missing skills to strengthen your application."
    return f"Low match. Only {matched} skills align. Review the requirements carefully."
