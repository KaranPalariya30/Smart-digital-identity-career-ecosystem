"""
The analysis pipeline as ONE plain function with no web code in it.
FastAPI calls it today; an agent can call it as a tool tomorrow.
"""
import time

from ..config import settings
from ..core import scorer
from ..core.feedback import generate_feedback
from ..core.jd_resolver import ResolvedJD
from ..core.skill_graph import learning_order
from ..core.skill_trie import matcher
from ..core.skills_db import CANONICAL_CATEGORY, PATTERN_TO_CANONICAL
from ..schemas import AnalysisResponse


def _by_category(skills) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for s in sorted(skills):
        out.setdefault(CANONICAL_CATEGORY[s], []).append(s)
    return out


def _normalise_verified(verified_skills: list[str]) -> set[str]:
    return {PATTERN_TO_CANONICAL[v.strip().lower()]
            for v in verified_skills if v.strip().lower() in PATTERN_TO_CANONICAL}


def extract_resume_skills(resume_text: str) -> dict[str, int]:
    """Tool-friendly helper: {canonical skill: mentions}."""
    return dict(matcher.count(resume_text))


def analyze(resume_text: str, jd: ResolvedJD, *, mode: str = "auto",
            verified_skills: list[str] | None = None) -> AnalysisResponse:
    t0 = time.perf_counter()

    resume_counts = extract_resume_skills(resume_text)
    resume_skills = set(resume_counts)
    jd_weights = jd.skill_weights
    jd_skills = set(jd_weights)
    verified = _normalise_verified(verified_skills or [])

    matched = sorted(resume_skills & jd_skills, key=lambda s: (-jd_weights[s], s))
    missing = sorted(jd_skills - resume_skills, key=lambda s: (-jd_weights[s], s))
    bonus = sorted(resume_skills - jd_skills)

    skill_score = scorer.weighted_skill_score(resume_skills, jd_weights)
    skill_pct = round(100 * len(matched) / len(jd_skills), 1) if jd_skills else 0.0
    text = scorer.text_similarity(resume_text, jd.text)

    overall = round(100 * scorer.combine(skill_score, text["text_score"], bool(jd_skills)))
    overall = max(0, min(100, overall))

    verified_pct = round(100 * len([s for s in matched if s in verified]) / len(matched), 1) if matched else 0.0

    def info(skill: str) -> dict:
        return {"name": skill, "category": CANONICAL_CATEGORY[skill],
                "count": resume_counts.get(skill, 0), "weight": jd_weights.get(skill, 0.0),
                "verified": skill in verified}

    fb = generate_feedback(overall, skill_pct, matched, missing, text["missing_keywords"],
                           len(text["matched_keywords"]), verified_pct or None)
    path = learning_order({s: jd_weights[s] for s in missing}, resume_skills)

    return AnalysisResponse.model_validate({
        "score": {
            "overall": overall,
            "grade": scorer.score_to_grade(overall),
            "skill_score": round(skill_score, 4),
            "text_score": round(text["text_score"], 4),
            "cosine_similarity": round(text["cosine"], 4),
            "keyword_coverage": round(text["coverage"], 4),
            "summary": scorer.summary_line(overall, len(matched), len(missing)),
        },
        "keywords": {
            "matched": text["matched_keywords"], "missing": text["missing_keywords"],
            "resume_top": text["resume_top"], "jd_top": text["jd_top"],
        },
        "skills": {
            "matched": [info(s) for s in matched],
            "missing": [info(s) for s in missing],
            "bonus": [info(s) for s in bonus[:15]],
            "match_percentage": skill_pct,
            "weighted_match_percentage": round(100 * skill_score, 1),
            "verified_percentage": verified_pct,
            "resume_by_category": _by_category(resume_skills),
            "jd_by_category": _by_category(jd_skills),
        },
        "feedback": fb,
        "learning_path": path,
        "meta": {
            "mode": mode, "jd_source": jd.source, "role_id": jd.role_id,
            "role_title": jd.role_title, "scoring_version": settings.scoring_version,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        },
    })
