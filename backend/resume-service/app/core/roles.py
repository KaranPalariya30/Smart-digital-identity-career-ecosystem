"""
Role profiles: the no-manual-JD building block.

A role = required skills (weight 3) + preferred skills (weight 1).
Later, an agent can build/refresh these from live job postings. The rest of
the code only sees the Role dataclass, so nothing else has to change.
"""
import json
from dataclasses import dataclass, field
from functools import lru_cache

from ..config import settings
from .min_heap import top_k_largest

REQUIRED_WEIGHT = 3.0
PREFERRED_WEIGHT = 1.0


@dataclass(frozen=True)
class Role:
    id: str
    title: str
    description: str
    required: tuple[str, ...]
    preferred: tuple[str, ...]
    weights: dict[str, float] = field(default_factory=dict, compare=False)

    def jd_text(self) -> str:
        """Synthetic JD used for the text-similarity half of the score."""
        return (f"{self.title}. {self.description} "
                f"Required skills: {', '.join(self.required)}. "
                f"Preferred skills: {', '.join(self.preferred)}.")


@lru_cache(maxsize=1)
def load_roles() -> dict[str, Role]:
    raw = json.loads(settings.roles_path.read_text(encoding="utf-8"))
    roles = {}
    for rid, r in raw.items():
        weights = {s: PREFERRED_WEIGHT for s in r["preferred"]}
        weights.update({s: REQUIRED_WEIGHT for s in r["required"]})   # required wins
        roles[rid] = Role(rid, r["title"], r["description"],
                          tuple(r["required"]), tuple(r["preferred"]), weights)
    return roles


def get_role(role_id: str) -> Role | None:
    return load_roles().get(role_id)


def rank_roles(resume_skills: set[str], top_k: int = 3) -> list[dict]:
    """Score every role by weighted skill coverage, keep the top K with our own min-heap (O(R log K))."""
    scored = []
    for role in load_roles().values():
        total = sum(role.weights.values())
        got = sum(w for s, w in role.weights.items() if s in resume_skills)
        scored.append((got / total, role))
    best = top_k_largest(scored, top_k, key=lambda t: (t[0], t[1].id))
    out = []
    for score, role in best:
        out.append({
            "role_id": role.id,
            "title": role.title,
            "fit_score": round(score * 100),
            "matched_skills": sorted(s for s in role.weights if s in resume_skills),
            "missing_required": [s for s in role.required if s not in resume_skills],
        })
    return out
