# Local Setup

## 1. Blockchain (Hardhat)

```bash
cd blockchain
cp .env.example .env
npm install
npx hardhat compile
npx hardhat test
```

In one terminal, start the local chain (keep it running):

```bash
npx hardhat node
```

In a second terminal, deploy and seed a demo issuer:

```bash
npm run deploy:localhost
npm run seed:localhost
```

`deploy:localhost` writes `blockchain/deployments/localhost-deployment.json`
containing the deployed contract address and ABI — the Python service reads
this file directly, so you don't need to copy the ABI by hand.

Copy the printed contract address into `blockchain/.env` as
`CONTRACT_ADDRESS` (optional locally, but required if you later deploy to a
testnet).

Run the presentation demo end-to-end (registers, verifies, tampers,
verifies again, revokes, verifies again):

```bash
npm run demo
```

## 2. Backend blockchain service (FastAPI)

```bash
cd backend/blockchain-service
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `ISSUER_PRIVATE_KEY` — use the demo issuer key printed by
  `npm run seed:localhost` (Hardhat's well-known local test account #1).
  **Never use a real private key here.**
- `DATABASE_URL` — point at your local Postgres instance.
- `DEPLOYMENT_ARTIFACT_PATH` — leave as default if you're running both
  services from the repo root layout described in `architecture.md`.

Apply the database migration:

```bash
psql "$DATABASE_URL" -f ../../database/migrations/001_create_credentials_table.sql
```

Start the service:

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: `http://localhost:8000/docs`

## 3. Environment variables reference

| Variable | Where | Purpose |
|---|---|---|
| `LOCAL_RPC_URL` | `blockchain/.env` | Local Hardhat RPC endpoint |
| `TESTNET_RPC_URL` / `DEPLOYER_PRIVATE_KEY` | `blockchain/.env` | Optional, only for a real testnet deploy |
| `CONTRACT_ADDRESS` | both `.env` files | Deployed contract address |
| `RPC_URL` | `backend/blockchain-service/.env` | Same chain the service should talk to |
| `ISSUER_PRIVATE_KEY` | `backend/blockchain-service/.env` | Account the service signs write transactions with |
| `DATABASE_URL` | `backend/blockchain-service/.env` | Postgres connection string |
| `FRONTEND_VERIFY_BASE_URL` | `backend/blockchain-service/.env` | Base URL QR codes point to |

No private keys or secrets are committed — `.env` is gitignored in both
`blockchain/` and `backend/blockchain-service/`.
