<!--
  Paste this section into the project's main README.md (append to the
  existing content — do not replace it). I couldn't fetch your actual
  README from GitHub in this sandbox (private/unauthenticated clone was
  blocked), so this is delivered as a separate snippet for you to merge in.
-->

## Blockchain Module (Credential Verification)

The `blockchain/` directory implements tamper-resistant academic/
professional credential verification using a Solidity smart contract
(`CredentialRegistry.sol`) deployed to a local Hardhat network, integrated
with the backend via `backend/blockchain-service/` (FastAPI + web3.py).

- Certificates are hashed (SHA-256) off-chain; only the hash, a
  credential ID, issuer address, timestamp, and revocation flag go
  on-chain — never the certificate itself or any PII.
- Verification is exposed via QR code: scanning it opens a verification
  page that checks the credential's hash and status against the chain.
- Full docs: [`docs/blockchain/`](docs/blockchain/)
- Setup: [`docs/blockchain/setup.md`](docs/blockchain/setup.md)

```bash
# Smart contract
cd blockchain && npm install && npx hardhat test

# Backend service
cd backend/blockchain-service && pip install -r requirements.txt
```
