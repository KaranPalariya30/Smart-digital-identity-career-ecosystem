# AI-Powered Smart Digital Identity and Career Ecosystem

AI-powered digital identity and career ecosystem integrating Generative AI, Machine Learning, Blockchain, and Cloud Computing for credential verification and personalized career development.

A student's credentials are sealed on a blockchain, anyone can verify them, and the sealed skills strengthen the student's AI resume analysis.

```
 Browser ── React app (:5173) ──┬── auth-service        (:8000)  accounts, JWT login, roles
                                ├── blockchain-service  (:8001)  issue / verify / revoke ──► CredentialRegistry.sol
                                └── resume-service      (:8002)  skills, scoring, learning path
```

## Quick start

Needs Python 3.10 to 3.13 (3.12 recommended; newer versions lack prebuilt wheels for the pinned packages) and Node.js 18+.

```bash
python scripts/dev.py setup     # once: virtualenvs, packages, .env files
python scripts/dev.py start     # local chain + contract + 3 services + frontend
python scripts/dev.py check     # rehearse the full demo flow (21 checks)
```

Open <http://localhost:5173>. Demo logins (local only): `admin@example.com / Admin@12345`, `student@example.com / Student@12345`, `recruiter@example.com / Recruiter@12345`.

## Repository layout

| Path | What it is |
|---|---|
| `frontend/` | React + Vite app ("Credia") |
| `backend/auth-service/` | FastAPI: registration, email verification, JWT login, roles |
| `backend/blockchain-service/` | FastAPI + web3.py: credential issue, verify, revoke, QR codes |
| `backend/resume-service/` | FastAPI + spaCy: resume analysis, role fit, learning path |
| `blockchain/` | Solidity contract and Hardhat project |
| `database/migrations/` | SQL for Postgres deployments |
| `docs/` | Integration guide and blockchain docs |
| `scripts/` | `dev.py` launcher and `e2e_check.py` demo rehearsal |

## Documentation

- [Integration guide, architecture and demo script](docs/INTEGRATION.md)
- [Blockchain module](docs/blockchain/)
- [Frontend](frontend/README.md)

## Tests

Each service has its own pytest suite, and the contract has Hardhat tests (`.github/workflows/ci.yml` runs all of them):

```bash
cd backend/auth-service && python -m pytest
cd backend/blockchain-service && python -m pytest
cd backend/resume-service && python -m pytest
cd blockchain && npx hardhat test
```
