import pytest

from app.core import scorer
from app.core.jd_resolver import JDResolutionError, ModeNotAvailableError, resolve_jd
from app.core.pdf_reader import ResumeParseError, extract_text_from_pdf_bytes
from app.core.roles import load_roles, rank_roles
from app.core.skill_graph import PREREQS, learning_order
from app.core.skills_db import ALL_SKILLS
from app.core.tfidf import CorpusIdf, build_tfidf_for_pair

RESUME = """Python developer. Built REST APIs with FastAPI and Flask, PostgreSQL, Redis.
Docker, Git, Linux, CI/CD with GitHub Actions. Machine learning with pandas and numpy."""


def test_cosine_identical_and_disjoint():
    assert scorer.cosine_similarity({"a": 1.0, "b": 2.0}, {"a": 1.0, "b": 2.0}) == pytest.approx(1.0)
    assert scorer.cosine_similarity({"a": 1.0}, {"b": 1.0}) == 0.0
    assert scorer.cosine_similarity({}, {"b": 1.0}) == 0.0


def test_weighted_skill_score():
    w = {"python": 3, "docker": 1}
    assert scorer.weighted_skill_score({"python"}, w) == pytest.approx(0.75)
    assert scorer.weighted_skill_score(set(), w) == 0.0


def test_corpus_idf_downweights_common_words():
    corpus = CorpusIdf.from_documents([["python", "team"], ["java", "team"], ["go", "team"]])
    assert corpus.idf("team") < corpus.idf("python")
    r_vec, _ = build_tfidf_for_pair(["python", "team"], ["python"], corpus)
    assert r_vec["python"] > r_vec["team"]


def test_roles_only_use_known_skills():
    for role in load_roles().values():
        assert set(role.weights) <= ALL_SKILLS, role.id


def test_rank_roles_prefers_relevant_role():
    from app.services.analyzer import extract_resume_skills
    top = rank_roles(set(extract_resume_skills(RESUME)), 3)
    assert top[0]["role_id"] in {"backend_python", "ml_engineer", "data_scientist", "genai_engineer"}
    assert top == sorted(top, key=lambda r: -r["fit_score"])


def test_graph_is_valid_and_acyclic():
    assert {k for k in PREREQS} <= ALL_SKILLS
    assert all(set(v) <= ALL_SKILLS for v in PREREQS.values())
    # every skill orderable => no cycle (raises ValueError otherwise)
    learning_order({s: 1.0 for s in PREREQS}, set(), max_steps=999)


def test_learning_order_puts_prereqs_first():
    path = learning_order({"kubernetes": 3.0}, {"git"})
    names = [s["skill"] for s in path]
    assert names.index("linux") < names.index("docker") < names.index("kubernetes")
    assert path[-1]["kind"] == "target"


def test_learning_order_skips_known():
    names = [s["skill"] for s in learning_order({"fastapi": 2.0}, {"python", "rest api", "git"})]
    assert names == ["fastapi"]


def test_resolver_modes():
    assert resolve_jd("role", None, "devops").source == "role_profile"
    assert resolve_jd("auto", None, "devops").role_id == "devops"
    with pytest.raises(JDResolutionError):
        resolve_jd("jd", "too short", None)
    with pytest.raises(JDResolutionError):
        resolve_jd("role", None, "astronaut")
    with pytest.raises(JDResolutionError):
        resolve_jd("auto", None, None)
    with pytest.raises(ModeNotAvailableError):
        resolve_jd("agent", None, None)


def test_pdf_rejects_non_pdf_and_empty():
    with pytest.raises(ResumeParseError):
        extract_text_from_pdf_bytes(b"")
    with pytest.raises(ResumeParseError):
        extract_text_from_pdf_bytes(b"hello this is not a pdf")
