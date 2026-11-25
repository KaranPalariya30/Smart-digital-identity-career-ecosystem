#!/usr/bin/env python3
"""One-command local environment for the whole platform (Windows, macOS, Linux).

    python scripts/dev.py setup      # one time: venvs, packages, .env files
    python scripts/dev.py start      # chain + deploy + 3 services + frontend
    python scripts/dev.py check      # end-to-end rehearsal of the demo flow
    python scripts/dev.py stop       # stop anything left running

Only the standard library is used, so run it with any Python 3.10+.
"""
import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / ".run"
IS_WIN = sys.platform == "win32"

AUTH = ROOT / "backend" / "auth-service"
CHAIN_SVC = ROOT / "backend" / "blockchain-service"
RESUME = ROOT / "backend" / "resume-service"
CONTRACTS = ROOT / "blockchain"
FRONTEND = ROOT / "frontend"

PORTS = {"chain-node": 8545, "auth": 8000, "blockchain": 8001, "resume": 8002, "frontend": 5173}
ARTIFACT = CONTRACTS / "deployments" / "localhost-deployment.json"

# Public test key that every `hardhat node` prints as account #0. It controls only fake ETH on a
# throwaway local chain (deploy.js makes this account the contract's issuer). Never use it, or any
# key committed to a repo, on a real network.
HARDHAT_ACCOUNT_0_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# DEMO ONLY - local accounts so the presentation does not start with sign-up.
DEMO_USERS = [
    ("Demo Admin", "admin@example.com", "Admin@12345", "ADMIN"),
    ("Demo Student", "student@example.com", "Student@12345", "STUDENT"),
    ("Demo Recruiter", "recruiter@example.com", "Recruiter@12345", "RECRUITER"),
]


# ----------------------------------------------------------------- helpers
def say(msg: str) -> None:
    print(f"==> {msg}", flush=True)


def venv_python(service: Path) -> str:
    return str(service / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python"))


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        sys.exit(f"'{name}' was not found on PATH. Install Node.js 18+ (it provides npm and npx).")
    return path


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, check=True)
    except subprocess.CalledProcessError:
        hint = ""
        if "deploy:localhost" in cmd:
            hint = ("\nHardhat downloads the Solidity compiler on first use, so this step needs internet access "
                    "(binaries.soliditylang.org).")
        sys.exit(f"\nCommand failed in {cwd.relative_to(ROOT)}/: {' '.join(cmd)}{hint}")


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for(url: str, name: str, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.7)
    sys.exit(f"{name} did not come up at {url}. See .run/*.log")


def read_env(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def ensure_env(path: Path, example: Path, wanted: dict[str, str]) -> None:
    """Create .env from the example if missing, and fill any listed key that is empty."""
    if not path.exists():
        shutil.copyfile(example, path)
        say(f"created {path.relative_to(ROOT)}")
    lines = path.read_text(encoding="utf-8").splitlines()
    have = read_env(path)
    for key, value in wanted.items():
        if have.get(key):
            continue
        for i, line in enumerate(lines):
            if line.split("=", 1)[0].strip() == key:
                lines[i] = f"{key}={value}"
                break
        else:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if IS_WIN:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass


def spawn(name: str, cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.Popen:
    RUN.mkdir(exist_ok=True)
    log = open(RUN / f"{name}.log", "w", encoding="utf-8")
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
    proc = subprocess.Popen(cmd, cwd=cwd, env={**os.environ, **(env or {})}, stdout=log, stderr=subprocess.STDOUT, **kwargs)
    pids = json.loads((RUN / "pids.json").read_text()) if (RUN / "pids.json").exists() else {}
    pids[name] = proc.pid
    (RUN / "pids.json").write_text(json.dumps(pids))
    return proc


# ----------------------------------------------------------------- setup
def secret_from_env() -> str:
    return read_env(AUTH / ".env").get("SECRET_KEY", "")


def prepare_env() -> None:
    """Create .env files and fill blanks, with ONE shared secret so every service trusts the same logins."""
    ensure_env(AUTH / ".env", AUTH / ".env.example", {"SECRET_KEY": secrets.token_urlsafe(48)})
    ensure_env(
        CHAIN_SVC / ".env", CHAIN_SVC / ".env.example",
        {"AUTH_SECRET_KEY": secret_from_env(), "SERVICE_API_TOKEN": secrets.token_urlsafe(32),
         "ISSUER_PRIVATE_KEY": HARDHAT_ACCOUNT_0_KEY},
    )


def cmd_setup(_args) -> None:
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 or newer is required.")
    tool("node"); npm = tool("npm")

    # 1. env files
    prepare_env()

    # 2. one virtualenv per Python service (their pinned dependencies conflict)
    for svc in (AUTH, CHAIN_SVC, RESUME):
        if not Path(venv_python(svc)).exists():
            say(f"creating virtualenv for {svc.name}")
            run([sys.executable, "-m", "venv", ".venv"], svc)
        say(f"installing {svc.name} requirements")
        run([venv_python(svc), "-m", "pip", "install", "-q", "-r", "requirements.txt"], svc)
    say("downloading the spaCy model for the resume service")
    run([venv_python(RESUME), "-m", "spacy", "download", "en_core_web_sm"], RESUME)

    # 3. node packages
    for folder in (CONTRACTS, FRONTEND):
        say(f"npm install in {folder.name}/")
        run([npm, "install", "--no-audit", "--no-fund"], folder)
    say("setup complete. Next: python scripts/dev.py start")


# ----------------------------------------------------------------- start / stop
def cmd_start(args) -> None:
    if not (AUTH / ".env").exists() or not Path(venv_python(RESUME)).exists():
        sys.exit("Run 'python scripts/dev.py setup' first.")
    prepare_env()   # fills any blank key left by an older setup
    npm, npx = tool("npm"), tool("npx")
    procs: list[subprocess.Popen] = []

    try:
        # 1. local blockchain + contract
        node_running = port_open(PORTS["chain-node"])
        if node_running:
            say("a local chain is already running on :8545, reusing it")
        else:
            say("starting the local blockchain (Hardhat node)")
            procs.append(spawn("chain-node", [npx, "hardhat", "node"], CONTRACTS))
            wait_for_port(PORTS["chain-node"], "Hardhat node")
        if not args.skip_deploy and (not node_running or not ARTIFACT.exists()):
            say("deploying CredentialRegistry (first run downloads the Solidity compiler)")
            run([npm, "run", "deploy:localhost"], CONTRACTS)

        # 2. demo accounts
        say("creating demo accounts")
        for name, email, pw, role in DEMO_USERS:
            run([venv_python(AUTH), "scripts/create_user.py", "--name", name, "--email", email,
                 "--password", pw, "--role", role], AUTH)

        # 3. services
        secret = secret_from_env()
        say("starting auth (:8000), blockchain (:8001), resume (:8002)")
        procs.append(spawn("auth", [venv_python(AUTH), "-m", "uvicorn", "app.main:app", "--port", "8000"], AUTH))
        procs.append(spawn("blockchain", [venv_python(CHAIN_SVC), "-m", "uvicorn", "app.main:app", "--port", "8001"], CHAIN_SVC))
        procs.append(spawn(
            "resume", [venv_python(RESUME), "-m", "uvicorn", "app.main:app", "--port", "8002"], RESUME,
            env={"AUTH_ENABLED": "true", "JWT_SECRET": secret},
        ))
        wait_for("http://127.0.0.1:8000/", "auth service")
        wait_for("http://127.0.0.1:8001/health", "blockchain service")
        wait_for("http://127.0.0.1:8002/health", "resume service")

        # 4. frontend
        say("starting the frontend (:5173)")
        procs.append(spawn("frontend", [npm, "run", "dev"], FRONTEND))
        wait_for("http://localhost:5173/", "frontend")

        print("\n" + "=" * 64)
        print(" Platform is up:  http://localhost:5173")
        print(" API docs:        :8000/docs (auth)  :8001/docs (chain)  :8002/docs (resume)")
        print(" Demo logins (local only):")
        for _, email, pw, role in DEMO_USERS:
            print(f"   {role:<10} {email}  /  {pw}")
        print(" Rehearse the demo:  python scripts/dev.py check")
        print(" Logs: .run/*.log      Stop: Ctrl+C")
        print("=" * 64, flush=True)
        while True:
            time.sleep(1)
            dead = [p for p in procs if p.poll() is not None]
            if dead:
                sys.exit("A service exited unexpectedly. See .run/*.log")
    except KeyboardInterrupt:
        print()
    finally:
        say("stopping")
        for p in procs:
            kill_tree(p)


def wait_for_port(port: int, name: str, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(port):
            return
        time.sleep(0.5)
    sys.exit(f"{name} did not open port {port}. See .run/*.log")


def cmd_stop(_args) -> None:
    f = RUN / "pids.json"
    if not f.exists():
        return say("nothing recorded as running")
    for name, pid in json.load(open(f)).items():
        try:
            if IS_WIN:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            else:
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            say(f"stopped {name}")
        except (ProcessLookupError, PermissionError):
            pass
    f.unlink()


def cmd_check(args) -> None:
    sys.exit(subprocess.run([sys.executable, str(ROOT / "scripts" / "e2e_check.py"), *args.rest]).returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup").set_defaults(fn=cmd_setup)
    st = sub.add_parser("start"); st.add_argument("--skip-deploy", action="store_true"); st.set_defaults(fn=cmd_start)
    sub.add_parser("stop").set_defaults(fn=cmd_stop)
    ck = sub.add_parser("check"); ck.add_argument("rest", nargs=argparse.REMAINDER); ck.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
