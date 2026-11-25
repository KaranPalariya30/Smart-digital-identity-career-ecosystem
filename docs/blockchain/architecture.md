# Blockchain Architecture

## Why blockchain is used

Credentials issued by the platform (certificates, transcripts, training
records) need to be verifiable by a third party — an employer, another
institution — without that party having to trust the issuing platform's
database directly. A centralized database can be edited quietly; a
blockchain record, once written, can't be silently altered without the
change being detectable. The blockchain here isn't storing the credential —
it's acting as a public, append-only **notary** for a hash of it.

## Why hashes are stored instead of certificates

Two independent reasons:

1. **Cost and scale.** On-chain storage is expensive and blockchains are a
   poor fit for large binary blobs like PDFs or images.
2. **Privacy.** Blockchains (even permissioned ones used for a class
   project) are effectively public and immutable — anything written to them
   is very hard to remove. Certificates typically contain personal data
   (name, DOB, sometimes ID numbers). Putting that on-chain would be
   irreversible exposure. Instead we store only a SHA-256 hash of the
   document. A hash reveals nothing about the document's contents, but any
   change to the document — even a single byte — produces a completely
   different hash, so it still proves tampering.

See `docs/blockchain/security.md`-equivalent notes in `smart-contract.md`
for the exact on-chain field list and what is deliberately excluded.

## Component overview

```text
                    FRONTEND
                       |
                       v
                 BACKEND API  (existing services + blockchain-service)
                       |
          +------------+------------+
          |                         |
          v                         v
      DATABASE               BLOCKCHAIN SERVICE (backend/blockchain-service)
   (app metadata,                   |
    document_hash,                  v
    tx hash, status)          web3.py -> JSON-RPC
                                     |
                                     v
                          CredentialRegistry.sol
                                     |
                                     v
                          Local Hardhat network
                       (swappable for a real testnet later)
```

- **`blockchain/`** — the Solidity contract, its tests, and deploy/seed/demo
  scripts. Fully self-contained; runs against a local Hardhat node with no
  real cryptocurrency required.
- **`backend/blockchain-service/`** — a small FastAPI service that is the
  only part of the system that talks to the chain. It signs transactions
  with an issuer account, computes/verifies SHA-256 hashes, generates QR
  codes, and persists off-chain metadata to Postgres.
- **`database/`** — the `credentials` table holding everything the app needs
  beyond what's on-chain (see `verification-flow.md`).

## Why this split

Keeping all chain interaction inside one service (rather than scattering
`web3.py` calls across other backend services) means:

- Only one place needs the issuer's private key / RPC config.
- Other services (auth-service, user-service) call this service over HTTP
  instead of needing blockchain dependencies themselves.
- The contract or even the chain itself (e.g. moving from Hardhat-local to a
  public testnet) can change without touching unrelated services.
