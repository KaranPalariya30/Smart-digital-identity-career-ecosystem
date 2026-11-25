# blockchain-service

FastAPI microservice that is the only part of the backend that talks to
`CredentialRegistry.sol`. See [`../../docs/blockchain/`](../../docs/blockchain/)
for full architecture and flow docs, and
[`../../docs/blockchain/setup.md`](../../docs/blockchain/setup.md) for setup.

## Endpoints

```text
POST /api/blockchain/credentials                    register (issuer only — wire auth)
GET  /api/blockchain/credentials/{id}                fetch metadata
POST /api/blockchain/credentials/{id}/verify         public verification
POST /api/blockchain/credentials/{id}/revoke         revoke (issuer/admin only — wire auth)
GET  /health
```

## Structure

```text
app/
  main.py               FastAPI app + router registration
  config.py              env settings + deployment-artifact loader
  blockchain_client.py    web3.py wrapper (sign/send/read against the contract)
  hashing.py               SHA-256 helper
  qr.py                     QR code generation
  database.py                SQLAlchemy model + session
  schemas.py                  Pydantic request/response models
  routers/credentials.py       the four endpoints above
static/verify-demo.html          throwaway verification page (replace with real frontend)
```

## Auth

This service does not implement authentication itself. Registration and
revocation are meant to sit behind the existing (or future) auth-service —
add a dependency like `Depends(require_role("issuer"))` to those two routes
once that service exists. Verification is intentionally left public.
