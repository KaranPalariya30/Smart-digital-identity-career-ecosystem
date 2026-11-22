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
| Register | `POST /api/auth/register` | auth |
| Verify email | `POST /api/auth/verify-email` | auth |
| Log in | `POST /api/auth/login` | auth |
| Session | `GET /api/auth/me` (Bearer JWT) | auth |
| Access check | `GET /api/auth/{student,recruiter,admin}-only` | auth |
| Forgot / reset password | `POST /api/auth/forgot-password`, `POST /api/auth/reset-password` | auth |
| Issue credential | `POST /api/blockchain/credentials?user_id&certificate_name&certificate_type` (multipart `file`, service Bearer token) | blockchain |
| Credential details | `GET /api/blockchain/credentials/{id}` | blockchain |
| Verify | `POST /api/blockchain/credentials/{id}/verify` (optional multipart `file`) | blockchain |
| Revoke | `POST /api/blockchain/credentials/{id}/revoke` (service Bearer token) | blockchain |
| Status panel | `GET /` (auth), `GET /health` (blockchain) | both |
| Resume analysis | `POST /api/resume/analyze` | not built yet |

`vite.config.js` proxies these to `localhost:8000` (auth), `8001` (blockchain) and `8002` (resume), so no CORS setup is needed in dev. Change the ports if yours differ.

## SHA-256 in the UI

`src/hash.js` hashes files in the browser with the Web Crypto API and formats the result exactly like `blockchain-service/app/hashing.py`: `0x` + 64 lowercase hex characters.

- **Landing:** a live demo. Edit the text and every changed character of the fingerprint flashes.
- **Issuer console:** the file is fingerprinted when you choose it. After sealing, the browser hash and the server's `document_hash` are shown side by side with a match badge.
- **`/verify/:id`:** add the original file to see its fingerprint and whether it matches the one sealed on the chain. A forged file shows a red fingerprint and `INVALID`.

Hashing needs a secure context: `https://` or `localhost`.

## Trying the issuer console

Registration only creates STUDENT users, so promote one for testing:

```sql
UPDATE users SET role = 'ADMIN' WHERE email = 'you@example.com';
```

Then log in, open **Issuer console**, and enter the `SERVICE_API_TOKEN` from blockchain-service's `.env`.

## Backend notes

1. Register and revoke need the service token, not a user JWT. The console keeps it in `sessionStorage` for development. In production, route these through your backend.
2. `credentials.user_id` is a UUID, but auth users have integer IDs. They need aligning before credentials can belong to accounts. The console has a "New" button that generates a UUID for testing.
3. `GET /credentials/{id}` returns the contract address in its `issuer` field, so the UI labels it "Contract". It also doesn't return `document_hash`. Adding it would let `/verify/:id` show the recorded fingerprint next to the one from the user's file.
4. Neither service sets CORS headers. Add `CORSMiddleware` before hosting the frontend on another origin.
5. Set `FRONTEND_VERIFY_BASE_URL=http://localhost:5173/verify` so QR codes open `/verify/:id`.
6. Resume analysis has no HTTP endpoint yet. The screen shows a clear message until `POST /api/resume/analyze` exists.
