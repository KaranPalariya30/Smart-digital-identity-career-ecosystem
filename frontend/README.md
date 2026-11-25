# Credia frontend

React + Vite frontend for the Smart Digital Identity & Career Ecosystem, wired to the
FastAPI services on `feature/authentication` and `feature/blockchain-verification`.
Drop this folder into the repo as `frontend/` (branch `feature/frontend-dashboard`).

```bash
npm install
npm run dev      # http://localhost:5173
```

## Endpoints used (all calls live in `src/api.js`)

| Screen | Method and path | Service |
|---|---|---|
| Register / verify email / log in | `POST /api/auth/register`, `/verify-email`, `/login` | auth |
| Session | `GET /api/auth/me` (Bearer JWT) | auth |
| Forgot / reset password | `POST /api/auth/forgot-password`, `/reset-password` | auth |
| Issue credential (ADMIN) | `POST /api/blockchain/credentials?user_id&certificate_name&certificate_type&skills` (multipart `file`, user JWT) | blockchain |
| My credentials (any user) | `GET /api/blockchain/credentials/mine` (user JWT) | blockchain |
| Credential details / verify | `GET /api/blockchain/credentials/{id}`, `POST .../{id}/verify` (public) | blockchain |
| Revoke (ADMIN) | `POST /api/blockchain/credentials/{id}/revoke` (user JWT) | blockchain |
| Resume analysis | `GET /api/resume/roles`, `POST /api/resume/analyze` (user JWT) | resume |
| Status panel | `GET /` (auth), `GET /health` (blockchain, resume) | all |

`vite.config.js` proxies these to `localhost:8000` (auth), `8001` (blockchain) and `8002` (resume), so no CORS setup is needed in dev. `/api/resume/*` is rewritten to the resume service's versioned `/api/v1/*`. In production, put the same rules in your reverse proxy.

## SHA-256 in the UI

`src/hash.js` hashes files in the browser with the Web Crypto API and formats the result exactly like `blockchain-service/app/hashing.py`: `0x` + 64 lowercase hex characters.

- **Landing:** a live demo. Edit the text and every changed character of the fingerprint flashes.
- **Issuer console:** the file is fingerprinted when you choose it. After sealing, the browser hash and the server's `document_hash` are shown side by side with a match badge.
- **`/verify/:id`:** add the original file to see its fingerprint and whether it matches the one sealed on the chain. A forged file shows a red fingerprint and `INVALID`.

Hashing needs a secure context: `https://` or `localhost`.

## Trying the issuer console

`python scripts/dev.py start` (repo root) creates demo accounts, including `admin@example.com`. Log in as the admin, open **Issuer console**, enter the student's user ID (shown on the student's Overview tab), attach a document, and seal it. No separate token is needed: the blockchain service checks the logged-in user's role.

## Verified skills

When issuing, list the skills the credential proves (`python, react`). The student's **Resume** tab collects the skills from their *active* credentials and sends them to the resume service as `verified_skills`, so the analysis shows how much of the match is backed by the blockchain. Revoking a credential removes its skills from that list.

## Notes

1. Hashing needs a secure context (`https://` or `localhost`).
2. The dev proxy hides the fact that the services are on different ports. For a hosted demo, serve `frontend/dist` and add the same proxy rules, or set `CORS_ORIGINS` on each service.
3. `GET /credentials/{id}` returns the contract address in its `issuer` field, so the UI labels it "Contract". The on-chain issuer address comes back from `/verify`.
