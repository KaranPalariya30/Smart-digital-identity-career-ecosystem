# Integration guide

How the four modules fit together, how to run them, and how to present them.

## 1. Architecture

```
                        ┌──────────────────────── Browser ────────────────────────┐
                        │  React app (Vite dev server, :5173, proxies /api/*)       │
                        └───────┬───────────────────┬───────────────────┬──────────┘
                      /api/auth │     /api/blockchain│        /api/resume │
                                ▼                    ▼                    ▼
                        auth-service :8000   blockchain-service :8001  resume-service :8002
                        users, JWT, roles    issue / verify / revoke   skills, score, path
                                │                    │ web3.py
                                │                    ▼
                                │            Hardhat node :8545 ── CredentialRegistry.sol
                                ▼                    ▼
                           SQLite/Postgres      SQLite/Postgres
```

| Service | Port | Owns |
|---|---|---|
| auth-service | 8000 | Accounts, email verification, password reset, JWT login, roles (`STUDENT`, `RECRUITER`, `ADMIN`) |
| blockchain-service | 8001 | Credential records, SHA-256 hashing, on-chain registration, verification, revocation, QR codes |
| resume-service | 8002 | Skill extraction, role scoring, learning path |
| Hardhat node | 8545 | Local chain with the `CredentialRegistry` contract |
| frontend | 5173 | UI; dev proxy maps `/api/auth`, `/api/blockchain`, `/api/resume` (rewritten to `/api/v1`) |

### How the services trust each other

The auth-service signs a JWT at login. The other two services only **verify** it, with the same secret, and never call auth-service:

| Setting | Where | Must equal |
|---|---|---|
| `SECRET_KEY` | `backend/auth-service/.env` | the source of truth |
| `AUTH_SECRET_KEY` | `backend/blockchain-service/.env` | `SECRET_KEY` |
| `JWT_SECRET` (+ `AUTH_ENABLED=true`) | resume-service environment | `SECRET_KEY` |

`python scripts/dev.py setup` generates one secret and writes it to all three.

| Action | Who may do it |
|---|---|
| Issue or revoke a credential | `ADMIN` (configurable with `ISSUER_ROLES`), or the static `SERVICE_API_TOKEN` for scripts |
| List own credentials (`/mine`) | any logged-in user, own records only |
| Analyze a resume | any logged-in user |
| Verify a credential | anyone (employers have no account) |

Only auth-service **access** tokens are accepted. Email-verification and password-reset tokens share the signing key but carry a different `purpose` and are rejected.

### The link between blockchain and resume

When an admin issues a credential they list the skills it proves (`python, react`). The student's Resume tab sends the skills from their *active* credentials as `verified_skills`. The analysis then shows what percentage of matched skills is backed by a sealed credential. Revoking a credential removes its skills from that list.

## 2. Running it

```bash
python scripts/dev.py setup     # once
python scripts/dev.py start     # Ctrl+C stops everything
python scripts/dev.py check     # rehearsal
```

`start` runs a Hardhat node, deploys the contract (the first deploy downloads the Solidity compiler, so it needs internet), creates the demo accounts, starts the three services and the frontend, and prints the URLs. Logs are in `.run/*.log`.

Each Python service has its own virtualenv because their pinned dependencies conflict.

## 3. Demo script (about 5 minutes)

1. **Architecture.** Show the diagram above. Point out that only a hash goes on-chain, never the document or any personal data.
2. **Student signs up.** Register, verify email (dev mode shows the token), log in. Note the **User ID** chip on the Overview tab.
3. **Role guard.** Log in as `admin@example.com`. Open **Issuer console**, enter the student's user ID, a certificate name, skills (`python, fastapi`), attach a PDF, and seal it. Show the QR code and that the browser and server fingerprints match.
4. **Public verification.** Open the verification page (no login). Verify with the original PDF: *Credential verified*. Edit the PDF and verify again: *Document doesn't match*.
5. **Student view.** Log in as the student. **My credentials** lists the credential.
6. **Resume analysis.** Open **Resume**, paste a resume, pick a role, analyze. The result shows the score, matched and missing skills, a learning order, and the share of skills **verified by the blockchain**.
7. **Revocation.** As admin, revoke the credential. Verify again: *Credential revoked*. Re-run the resume analysis: the verified share drops.

`python scripts/dev.py check` runs this same flow through the real services in a few seconds. Run it before presenting.

## 4. What the integration changed

| Gap | Fix |
|---|---|
| Code split across six branches, empty `develop`, one-line README | Merged into one tree, layout under `backend/`, new README and this guide |
| Frontend called `/api/resume/analyze` with `file`/`text`; service expects `/api/v1/analyze` with `resume_file`/`resume_text` plus a role or job description | Proxy rewrites the path; the Resume screen sends the right fields and has a role picker |
| Issuing needed a static token pasted into the browser | Blockchain service accepts the logged-in admin's JWT and checks the role |
| Resume service used a separate JWT setting, no `purpose` check, auth off by default; legacy `/analyze` route bypassed it | Shared secret, access-token check, fails closed when the secret is missing, legacy route protected |
| `credentials.user_id` was a UUID; auth ids are integers | Stored as text; migration `002` for Postgres |
| No CORS on auth/blockchain; resume allowed `*` | Origins limited to the frontend by default (`CORS_ORIGINS`) |
| Credential detail omitted the document hash | Included, shown on the verify page |
| Blockchain service needed Postgres | SQLite by default, Postgres still supported |
| Admin accounts needed hand-written SQL | `backend/auth-service/scripts/create_user.py` |
| `ISSUER_PRIVATE_KEY` blank in `.env.example` gave a 500 on first issue | `dev.py` fills the public Hardhat test key for local use; the API now returns a clear 503 when the chain or key is missing |
| `.gitignore` excluded every `.env.example` | Fixed; compiled contract output and the local deployment file are ignored |
| CI covered only auth, on two branches | One workflow for all services, the contract and the frontend build |

## 5. Known limitations and next steps

- **Logout is not instant in the other services.** Auth-service checks `token_version` in its database; the other two only verify the signature and expiry, so a revoked session stays valid until the token expires (60 minutes by default). Fix: have them call `GET /api/auth/me`, or use short-lived tokens.
- **Demo accounts and the Hardhat key are for local use only.** Do not deploy them. Production needs a secrets manager for `SECRET_KEY` and `ISSUER_PRIVATE_KEY`, and a real chain or testnet.
- **The uploaded certificate is hashed and discarded.** `file_path` is not wired to storage yet, so the original file is not kept by the platform. The holder keeps it and re-uploads it to verify.
- **The admin must know the student's numeric user ID.** There is no user lookup endpoint yet.
- **Skills are free text on the credential.** Entries not in the resume service's skill list are ignored.
- **Career-path data** in the frontend (`branches.js`) is static.
- The legacy `/ui` page of the resume service does not send a token, so it only works with `AUTH_ENABLED=false`.
