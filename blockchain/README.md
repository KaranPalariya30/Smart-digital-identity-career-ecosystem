# Blockchain Module — Credential Verification

Solidity smart contract + Hardhat project implementing tamper-resistant
academic/professional credential verification for the Smart Digital
Identity and Career Ecosystem.

Full docs: [`../docs/blockchain/`](../docs/blockchain/)

## Quick start

```bash
npm install
npx hardhat compile
npx hardhat test
```

Local network + deploy:

```bash
npx hardhat node                                    # terminal 1, keep running
npm run deploy:localhost                             # terminal 2
npm run seed:localhost                                # authorizes a demo issuer
npm run demo                                           # full register->verify->tamper->revoke walkthrough
```

## Contents

```text
contracts/CredentialRegistry.sol   the contract
scripts/deploy.js                  deploys + writes deployments/<network>-deployment.json
scripts/seed.js                    authorizes a demo issuer account
scripts/demo.js                    end-to-end presentation demo
test/CredentialRegistry.test.js    full test suite
```

## Note on this environment's test run

Contract compilation was verified with the standalone `solc` npm package
(the sandbox this was built in couldn't reach
`binaries.soliditylang.org`, which Hardhat's own downloader needs) — it
compiles cleanly with no errors. `npx hardhat test` itself hasn't been run
in that sandbox for the same reason; run it locally where you have normal
internet access before relying on it for your presentation.
