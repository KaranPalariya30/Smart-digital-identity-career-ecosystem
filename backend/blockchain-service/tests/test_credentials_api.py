import pytest

from .conftest import bearer, make_token

URL = "/api/blockchain/credentials"
ADMIN = lambda: bearer(make_token(sub="1", role="ADMIN"))      # noqa: E731
STUDENT = lambda sub="7": bearer(make_token(sub=sub, role="STUDENT"))  # noqa: E731
PDF = ("cert.pdf", b"%PDF-1.4 original certificate bytes", "application/pdf")


def issue(client, headers, user_id="7", skills="Python, React ,python", file=PDF):
    params = {"user_id": user_id, "certificate_name": "Python Bootcamp", "certificate_type": "course"}
    if skills is not None:
        params["skills"] = skills
    return client.post(URL, params=params, files={"file": file}, headers=headers)


# ------------------------------------------------------------------ who may issue
def test_issue_requires_a_token(client):
    assert issue(client, {}).status_code == 401


def test_issue_rejects_student(client):
    r = issue(client, STUDENT())
    assert r.status_code == 403


def test_issue_rejects_wrong_signature_expired_and_non_access_tokens(client):
    for token in (
        make_token(role="ADMIN", secret="x" * 40),
        make_token(role="ADMIN", exp_in=-10),
        make_token(role="ADMIN", purpose="password_reset"),
        "not-a-jwt",
    ):
        assert issue(client, bearer(token)).status_code == 401


def test_admin_can_issue_and_skills_are_normalised(client, chain):
    r = issue(client, ADMIN())
    assert r.status_code == 201
    body = r.json()
    assert body["credential_id"].startswith("CRED-")
    assert body["document_hash"].startswith("0x") and len(body["document_hash"]) == 66
    assert body["skills"] == ["python", "react"]
    assert body["qr_code_base64"]
    assert body["verification_url"].endswith(body["credential_id"])
    assert body["credential_id"] in chain.ledger


def test_service_token_still_works_for_scripts(client):
    assert issue(client, bearer("test-service-token")).status_code == 201


def test_user_id_is_text_not_uuid_and_is_validated(client):
    assert issue(client, ADMIN(), user_id="42").status_code == 201
    assert issue(client, ADMIN(), user_id="bad id!").status_code == 422


# ------------------------------------------------------------------ my credentials
def test_mine_requires_login(client):
    assert client.get(f"{URL}/mine").status_code == 401


def test_mine_returns_only_own_credentials(client):
    issue(client, ADMIN(), user_id="7", skills="python")
    issue(client, ADMIN(), user_id="8", skills="java")
    mine = client.get(f"{URL}/mine", headers=STUDENT("7")).json()
    assert [c["skills"] for c in mine] == [["python"]]
    assert all("user_id" not in c for c in mine)


# ------------------------------------------------------------------ public reads
def test_detail_is_public_and_exposes_hash_but_not_user(client):
    cid = issue(client, ADMIN(), user_id="9").json()
    d = client.get(f"{URL}/{cid['credential_id']}").json()
    assert d["document_hash"] == cid["document_hash"]
    assert d["skills"] == ["python", "react"]
    assert "user_id" not in d
    assert client.get(f"{URL}/CRED-NOPE").status_code == 404


# ------------------------------------------------------------------ verification
def test_verify_valid_tampered_and_unknown(client):
    cid = issue(client, ADMIN()).json()["credential_id"]
    ok = client.post(f"{URL}/{cid}/verify", files={"file": PDF}).json()
    assert ok["status"] == "VERIFIED" and ok["issuer"]

    forged = ("cert.pdf", b"%PDF-1.4 FORGED", "application/pdf")
    assert client.post(f"{URL}/{cid}/verify", files={"file": forged}).json()["status"] == "INVALID"

    assert client.post(f"{URL}/{cid}/verify").json()["status"] == "VERIFIED"   # id only
    assert client.post(f"{URL}/CRED-NOPE/verify").json()["status"] == "NOT_FOUND"


def test_revoke_needs_issuer_and_flips_status(client):
    cid = issue(client, ADMIN()).json()["credential_id"]

    assert client.post(f"{URL}/{cid}/revoke").status_code == 401
    assert client.post(f"{URL}/{cid}/revoke", headers=STUDENT()).status_code == 403

    r = client.post(f"{URL}/{cid}/revoke", headers=ADMIN())
    assert r.status_code == 200 and r.json()["verification_status"] == "revoked"
    assert client.post(f"{URL}/{cid}/revoke", headers=ADMIN()).status_code == 409
    assert client.post(f"{URL}/{cid}/verify").json()["status"] == "REVOKED"
    assert client.get(f"{URL}/mine", headers=STUDENT("7")).json()[0]["verification_status"] == "revoked"


# ------------------------------------------------------------------ CORS + health
def test_cors_allows_the_frontend_origin_only(client):
    ok = client.options(URL, headers={"Origin": "http://localhost:5173",
                                      "Access-Control-Request-Method": "POST",
                                      "Access-Control-Request-Headers": "authorization"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(URL, headers={"Origin": "http://evil.example",
                                       "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ------------------------------------------------------------------ chain unavailable
def test_missing_signer_key_or_dead_node_is_a_503_not_a_500(client, chain):
    def boom(*_a):
        raise RuntimeError("ISSUER_PRIVATE_KEY is not configured")
    chain.register_credential = boom
    r = issue(client, ADMIN())
    assert r.status_code == 503 and "ISSUER_PRIVATE_KEY" in r.json()["detail"]
    # nothing was written to the database for the failed attempt
    assert client.get(f"{URL}/mine", headers=STUDENT("7")).json() == []
