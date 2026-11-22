import pytest
from fastapi.testclient import TestClient

from app.main import app

RESUME = ("Python developer with FastAPI, Flask and REST APIs. PostgreSQL, Redis, Docker, Git, "
          "Linux and CI/CD. Machine learning with pandas, numpy and scikit-learn. SQL.")
JD = ("We need a Python backend developer. Must know FastAPI or Flask, REST API design, "
      "PostgreSQL, Docker, Git and Kubernetes. CI/CD and AWS experience is a plus.")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_analyze_with_jd(client):
    r = client.post("/api/v1/analyze/text", json={"resume_text": RESUME, "jd_text": JD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0 <= body["score"]["overall"] <= 100
    assert body["meta"]["jd_source"] == "provided"
    assert "kubernetes" in [s["name"] for s in body["skills"]["missing"]]
    assert "fastapi" in [s["name"] for s in body["skills"]["matched"]]
    steps = [s["skill"] for s in body["learning_path"]]
    assert "kubernetes" in steps


def test_analyze_without_jd_uses_role(client):
    r = client.post("/api/v1/analyze/text", json={"resume_text": RESUME, "target_role": "backend_python"})
    assert r.status_code == 200, r.text
    assert r.json()["meta"]["jd_source"] == "role_profile"
    assert r.json()["meta"]["role_id"] == "backend_python"


def test_better_resume_scores_higher(client):
    weak = client.post("/api/v1/analyze/text",
                       json={"resume_text": "Retail assistant, customer service, cash handling.",
                             "target_role": "backend_python"}).json()["score"]["overall"]
    strong = client.post("/api/v1/analyze/text",
                         json={"resume_text": RESUME, "target_role": "backend_python"}).json()["score"]["overall"]
    assert strong > weak


def test_verified_skills_flagged(client):
    r = client.post("/api/v1/analyze/text", json={
        "resume_text": RESUME, "target_role": "backend_python", "verified_skills": ["Postgres", "python"]}).json()
    flags = {s["name"]: s["verified"] for s in r["skills"]["matched"]}
    assert flags["postgresql"] and flags["python"] and not flags["docker"]
    assert r["skills"]["verified_percentage"] > 0


def test_errors(client):
    assert client.post("/api/v1/analyze/text", json={"resume_text": RESUME}).status_code == 400
    assert client.post("/api/v1/analyze/text", json={"resume_text": RESUME, "target_role": "x"}).status_code == 400
    assert client.post("/api/v1/analyze/text", json={"resume_text": RESUME, "mode": "agent"}).status_code == 501
    assert client.get("/api/v1/roles/nope").status_code == 404


def test_roles_endpoints(client):
    roles = client.get("/api/v1/roles").json()
    assert len(roles) >= 5
    rec = client.post("/api/v1/roles/recommend/text", json={"resume_text": RESUME, "top_k": 2}).json()
    assert len(rec["recommendations"]) == 2
    assert "python" in rec["detected_skills"]


def test_multipart_text_and_bad_pdf(client):
    r = client.post("/api/v1/analyze", data={"resume_text": RESUME, "target_role": "devops"})
    assert r.status_code == 200
    bad = client.post("/api/v1/analyze", files={"resume_file": ("cv.pdf", b"not a pdf", "application/pdf")},
                      data={"target_role": "devops"})
    assert bad.status_code == 400


def test_pdf_upload_roundtrip(client):
    pypdf = pytest.importorskip("pypdf")
    from io import BytesIO
    # build a tiny text PDF by hand (no extra deps)
    content = b"BT /F1 12 Tf 72 720 Td (Python FastAPI Docker Git PostgreSQL) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell()); out.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref))
    r = client.post("/api/v1/analyze", files={"resume_file": ("cv.pdf", out.getvalue(), "application/pdf")},
                    data={"target_role": "backend_python"})
    assert r.status_code == 200, r.text
    assert "python" in [s["name"] for s in r.json()["skills"]["matched"]]


def test_legacy_shape(client):
    r = client.post("/analyze", json={"resume_text": RESUME, "jd_text": JD})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"success", "score", "keywords", "skills", "feedback"}
    assert isinstance(body["skills"]["matched"][0], str)
    assert client.post("/analyze", json={"resume_text": RESUME, "jd_text": "short"}).status_code == 400

