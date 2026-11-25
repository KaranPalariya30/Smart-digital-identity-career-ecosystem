#!/usr/bin/env python3
"""Rehearse the whole demo against the running platform (standard library only).

    python scripts/e2e_check.py                    # through the frontend proxy on :5173
    python scripts/e2e_check.py --base http://localhost:5173

Walks: register -> verify email -> login -> role guard -> issue (admin) ->
student sees credential -> public verify -> tamper detection -> resume analysis
with verified skills -> revoke -> verify again -> verified skills drop away.
Exits 1 if any step fails, so it is also safe to run just before presenting.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

ADMIN = ("admin@example.com", "Admin@12345")
RESUME_TEXT = (
    "Backend developer. Built REST APIs with Python and FastAPI, designed SQL schemas on PostgreSQL, "
    "wrote unit tests with pytest, containerised services with Docker and used Git daily. " * 2
)


class Http:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, method, path, *, token=None, body=None, content_type=None):
        req = urllib.request.Request(self.base + path, data=body, method=method)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        if content_type:
            req.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw[:200].decode(errors="replace")}
        except urllib.error.URLError as e:          # service down / refused: report, do not crash
            return 0, {"raw": str(getattr(e, "reason", e))}

    def json(self, method, path, payload=None, token=None):
        body = json.dumps(payload).encode() if payload is not None else None
        return self.call(method, path, token=token, body=body, content_type="application/json" if body else None)

    def form(self, method, path, fields=None, files=None, token=None):
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (fields or {}).items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (name, data) in (files or {}).items():
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n".encode() + data + b"\r\n"
            )
        parts.append(f"--{boundary}--\r\n".encode())
        return self.call(method, path, token=token, body=b"".join(parts),
                         content_type=f"multipart/form-data; boundary={boundary}")


results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   <- {detail}" if detail and not ok else ""))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:5173")
    base = ap.parse_args().base
    h = Http(base)
    print(f"Rehearsing against {base}\n")

    print("Services")
    for name, path in (("auth", "/svc/auth/"), ("blockchain", "/svc/chain/health"), ("resume", "/svc/resume/health")):
        code, _ = h.call("GET", path)
        check(code == 200, f"{name} service reachable", f"HTTP {code}")
    if not all(ok for ok, _ in results):
        print("\nStart the platform first:  python scripts/dev.py start")
        return 1

    print("\nAccounts and roles")
    email, pw = f"e2e-{int(time.time())}@example.com", "Student@12345"
    code, reg = h.json("POST", "/api/auth/register", {"name": "E2E Student", "email": email, "password": pw})
    check(code == 201 and reg.get("verification_token"), "student registers (dev mode returns the email token)", str(reg))
    code, _ = h.json("POST", "/api/auth/verify-email", {"token": reg.get("verification_token", "")})
    check(code == 200, "email verified", str(code))
    code, tok = h.json("POST", "/api/auth/login", {"email": email, "password": pw})
    student = tok.get("access_token")
    check(code == 200 and student, "student logs in", str(tok))
    code, me = h.json("GET", "/api/auth/me", token=student)
    sid = str(me.get("id"))
    check(code == 200 and me.get("role") == "STUDENT", f"student profile (user id {sid})")
    code, tok = h.json("POST", "/api/auth/login", {"email": ADMIN[0], "password": ADMIN[1]})
    admin = tok.get("access_token")
    check(code == 200 and admin, "admin logs in (demo account)", str(tok))
    if not (student and admin):
        return finish()

    print("\nCredential lifecycle")
    doc = b"%PDF-1.4 Python Bootcamp certificate, e2e run " + email.encode()
    q = f"?user_id={sid}&certificate_name=Python%20Bootcamp&certificate_type=course&skills=python,fastapi"
    code, body = h.form("POST", "/api/blockchain/credentials" + q, files={"file": ("cert.pdf", doc)}, token=student)
    check(code == 403, "a student CANNOT issue credentials", f"HTTP {code}")
    code, body = h.form("POST", "/api/blockchain/credentials" + q, files={"file": ("cert.pdf", doc)}, token=admin)
    cid = body.get("credential_id")
    check(code == 201 and cid and body.get("qr_code_base64"), "admin issues + seals a credential", str(body)[:200])
    if not cid:
        return finish()
    code, mine = h.json("GET", "/api/blockchain/credentials/mine", token=student)
    check(code == 200 and any(c["credential_id"] == cid for c in mine), "student sees it under My credentials")
    code, res = h.form("POST", f"/api/blockchain/credentials/{cid}/verify", files={"file": ("cert.pdf", doc)})
    check(res.get("status") == "VERIFIED", "public verify with the original file -> VERIFIED", str(res))
    code, res = h.form("POST", f"/api/blockchain/credentials/{cid}/verify", files={"file": ("cert.pdf", doc + b" TAMPERED")})
    check(res.get("status") == "INVALID", "public verify with a tampered file -> INVALID", str(res))

    print("\nResume analysis (verified skills from the blockchain credential)")
    def analyze(verified):
        fields = {"resume_text": RESUME_TEXT, "target_role": "backend_python", "mode": "role"}
        if verified:
            fields["verified_skills"] = ",".join(verified)
        return h.form("POST", "/api/resume/analyze", fields=fields, token=student)
    code, _ = h.form("POST", "/api/resume/analyze", fields={"resume_text": RESUME_TEXT, "target_role": "backend_python"})
    check(code == 401, "resume analysis requires login", f"HTTP {code}")
    skills = sorted({s for c in mine if c["verification_status"] == "active" for s in c["skills"]})
    code, out = analyze(skills)
    pct = out.get("skills", {}).get("verified_percentage", 0)
    check(code == 200 and out.get("score", {}).get("overall") is not None, "analysis returns a score", str(out)[:200])
    check(pct > 0, f"credential skills {skills} are counted as verified ({pct}%)")

    print("\nRevocation")
    code, rv = h.form("POST", f"/api/blockchain/credentials/{cid}/revoke", token=student)
    check(code == 403, "a student CANNOT revoke", f"HTTP {code}")
    code, rv = h.form("POST", f"/api/blockchain/credentials/{cid}/revoke", token=admin)
    check(code == 200, "admin revokes the credential", str(rv))
    code, res = h.form("POST", f"/api/blockchain/credentials/{cid}/verify", files={"file": ("cert.pdf", doc)})
    check(res.get("status") == "REVOKED", "verify now reports REVOKED", str(res))
    code, mine = h.json("GET", "/api/blockchain/credentials/mine", token=student)
    skills = sorted({s for c in mine if c["verification_status"] == "active" for s in c["skills"]})
    check(skills == [], "revoked credential no longer supplies verified skills", str(skills))
    return finish()


def finish() -> int:
    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("Failed: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
