"""
Terminal check against a RUNNING server (no extra packages needed).

    python scripts/smoke_test.py                       # http://127.0.0.1:8000
    python scripts/smoke_test.py http://127.0.0.1:8001

Exit code: 0 = all passed, 1 = a check failed, 2 = server not reachable.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

STRONG = ("Python developer. FastAPI, Flask, REST APIs, PostgreSQL, Redis, Docker, Git, Linux, "
          "CI/CD, SQL. Machine learning with pandas and numpy.")
WEAK = "Retail assistant. Customer service and cash handling."
JD = ("We need a Python backend developer with FastAPI, REST API design, PostgreSQL, Docker and "
      "Kubernetes experience. AWS is a plus.")


def call(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "null")


results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail and not ok else ""))


def main() -> int:
    try:
        status, body = call("GET", "/health")
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        print(f"Cannot reach {BASE}. Start the server first:\n"
              "  python -m uvicorn app.main:app --reload --port 8000")
        return 2
    check("GET /health", status == 200 and body.get("status") == "ok", str(body))

    status, roles = call("GET", "/api/v1/roles")
    check("GET /api/v1/roles lists roles", status == 200 and len(roles) >= 5, str(status))

    status, strong = call("POST", "/api/v1/analyze/text", {"resume_text": STRONG, "target_role": "backend_python"})
    ok = status == 200 and 0 <= strong["score"]["overall"] <= 100
    check("analyze with a role", ok, str(strong)[:120])

    status, weak = call("POST", "/api/v1/analyze/text", {"resume_text": WEAK, "target_role": "backend_python"})
    check("strong resume scores higher than weak",
          status == 200 and ok and strong["score"]["overall"] > weak["score"]["overall"])

    status, jd = call("POST", "/api/v1/analyze/text", {"resume_text": STRONG, "jd_text": JD})
    missing = [s["name"] for s in jd["skills"]["missing"]] if status == 200 else []
    check("analyze with a pasted JD finds missing skill", status == 200 and "kubernetes" in missing, str(missing))
    check("learning path is returned", status == 200 and len(jd["learning_path"]) > 0)

    status, rec = call("POST", "/api/v1/roles/recommend/text", {"resume_text": STRONG, "top_k": 3})
    check("role recommendation (no JD)", status == 200 and len(rec["recommendations"]) == 3, str(status))

    status, _ = call("POST", "/api/v1/analyze/text", {"resume_text": STRONG})
    check("no JD and no role -> 400", status == 400, str(status))
    status, _ = call("POST", "/api/v1/analyze/text", {"resume_text": STRONG, "mode": "agent"})
    check("mode=agent -> 501 (not built yet)", status == 501, str(status))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())