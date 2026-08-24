const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

// Reads deployments/<network>-deployment.json (written by deploy.js) and
// authorizes the second Hardhat test account as a demo issuer, so you can
// register credentials right away without extra setup.
async function main() {
  const deploymentFile = path.join(
    __dirname,
    "..",
    "deployments",
    `${hre.network.name}-deployment.json`
  );

  if (!fs.existsSync(deploymentFile)) {
    throw new Error(
      `No deployment found for network "${hre.network.name}". Run ` +
        `"npm run deploy:localhost" first.`
    );
  }

  const { address } = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
  const [admin, demoIssuer] = await hre.ethers.getSigners();

  const registry = await hre.ethers.getContractAt("CredentialRegistry", address);

  console.log(`Authorizing ${demoIssuer.address} as an issuer...`);
  const tx = await registry.connect(admin).authorizeIssuer(demoIssuer.address);
  await tx.wait();

  console.log("Done. Demo issuer authorized:");
  console.log(`  address: ${demoIssuer.address}`);
  console.log(
    "  (this is Hardhat's well-known local test account #1 — safe to log, " +
      "it only ever holds test ETH on your local node)"
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
