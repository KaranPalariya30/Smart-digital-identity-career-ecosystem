"""
Turns whatever the caller gave us into a ResolvedJD: text + weighted skills.

This is THE seam for agentic AI. Today there are two resolvers:
  * "jd"   - a JD pasted by the user
  * "role" - a predefined role profile (no JD needed)
Later you add an AgentJDResolver (builds a JD from live job postings, or from
the roles an agent infers from the resume) and register it:

    register_resolver("agent", AgentJDResolver(...))

Nothing else in the pipeline changes.
"""
from dataclasses import dataclass
from typing import Protocol

from ..config import settings
from .roles import get_role, load_roles
from .skill_trie import matcher


class JDResolutionError(ValueError):
    """Bad input (too-short JD, unknown role, ...) -> HTTP 400/404."""


class ModeNotAvailableError(RuntimeError):
    """Mode exists in the API contract but is not implemented yet -> HTTP 501."""


@dataclass(frozen=True)
class ResolvedJD:
    text: str
    skill_weights: dict[str, float]
    source: str                 # "provided" | "role_profile" | "agent" ...
    role_id: str | None = None
    role_title: str | None = None


class JDResolver(Protocol):
    def resolve(self, *, jd_text: str | None, target_role: str | None) -> ResolvedJD: ...


class ProvidedJDResolver:
    def resolve(self, *, jd_text, target_role) -> ResolvedJD:
        if not jd_text or len(jd_text.strip()) < settings.min_jd_chars:
            raise JDResolutionError(
                f"Job description must be at least {settings.min_jd_chars} characters."
            )
        counts = matcher.count(jd_text)
        # importance proxy: a skill mentioned more often matters more (capped at 2x)
        weights = {s: 1.0 + 0.5 * min(c - 1, 2) for s, c in counts.items()}
        return ResolvedJD(jd_text.strip(), weights, "provided")


class RoleProfileResolver:
    def resolve(self, *, jd_text, target_role) -> ResolvedJD:
        role = get_role(target_role or "")
        if role is None:
            raise JDResolutionError(
                f"Unknown target_role '{target_role}'. Valid roles: {', '.join(sorted(load_roles()))}."
            )
        return ResolvedJD(role.jd_text(), dict(role.weights), "role_profile", role.id, role.title)


_RESOLVERS: dict[str, JDResolver] = {
    "jd": ProvidedJDResolver(),
    "role": RoleProfileResolver(),
}


def register_resolver(mode: str, resolver: JDResolver) -> None:
    _RESOLVERS[mode] = resolver


def resolve_jd(mode: str, jd_text: str | None, target_role: str | None) -> ResolvedJD:
    """mode: auto | jd | role | agent"""
    if mode == "auto":
        if jd_text and jd_text.strip():
            mode = "jd"
        elif target_role:
            mode = "role"
        else:
            raise JDResolutionError("Provide either jd_text or target_role (or use /roles/recommend).")
    resolver = _RESOLVERS.get(mode)
    if resolver is None:
        raise ModeNotAvailableError(f"Mode '{mode}' is not available yet.")
    return resolver.resolve(jd_text=jd_text, target_role=target_role)
