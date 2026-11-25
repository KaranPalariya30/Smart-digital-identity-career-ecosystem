# Credential Registration, Verification & Revocation Flow

## Registration

```text
Issuer uploads certificate
        |
POST /api/blockchain/credentials
        |
Backend computes SHA-256 hash of the file (file itself is not persisted
here — wire file_path to real object storage when it exists)
        |
Backend calls CredentialRegistry.registerCredential(id, hash)
        |
Transaction mined -> tx hash returned
        |
Row inserted into `credentials` table (id, user, hash, tx hash, status=active)
        |
QR code generated, encoding the verification URL:
  {FRONTEND_VERIFY_BASE_URL}/{credentialId}
        |
Response: credential_id, document_hash, tx hash, verification_url, QR (base64 PNG)
```

## Verification (QR scan)

```text
Verifier scans QR -> opens {FRONTEND_VERIFY_BASE_URL}/{credentialId}
        |
Frontend calls POST /api/blockchain/credentials/{id}/verify
        |
Backend looks up the credential row (for the recorded hash + metadata)
        |
Backend queries CredentialRegistry.getCredential(id)
        |
Compare on-chain hash vs recorded/recomputed hash, check revoked flag
        |
Response status:
  VERIFIED    - exists, hash matches, not revoked
  REVOKED     - exists, hash matches, but revoked
  INVALID     - exists but hash does not match (tampered)
  NOT_FOUND   - no such credential
```

If the verifier has the original document in hand, they can instead POST it
to the same endpoint; the backend recomputes the hash from those bytes
rather than trusting the stored one — this is the strongest form of
verification and the one to use in the presentation demo's "tamper" step.

## Revocation

```text
Issuer/admin calls POST /api/blockchain/credentials/{id}/revoke
        |
Backend calls CredentialRegistry.revokeCredential(id)
        |
On success: `credentials.verification_status` set to 'revoked' in DB
        |
Any subsequent verify call now returns REVOKED
```

## Security considerations

- **No PII or file content on-chain** — see `architecture.md` and
  `smart-contract.md`.
- **Verification is public** (no auth) by design — anyone should be able to
  check a credential without a platform account, matching the spec.
- **Registration/revocation require the issuer's signing key**, held only by
  `backend/blockchain-service`. Route-level authorization (only letting
  authenticated issuer/admin users hit those endpoints) should be wired to
  the existing auth-service once it exists — this service does not
  implement its own auth.
- **Private keys are never hardcoded.** Local dev uses Hardhat's well-known
  test accounts (which only ever hold test ETH on a local chain); anything
  beyond local dev must come from a secrets manager.
- **Tamper detection is hash-based, not trust-based** — even a compromised
  backend can't produce a false "VERIFIED" result without also controlling
  the issuer's private key, since the authoritative comparison happens
  against the on-chain record.
