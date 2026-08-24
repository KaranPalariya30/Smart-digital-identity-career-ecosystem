const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [admin] = await hre.ethers.getSigners();

  console.log(`Deploying CredentialRegistry with admin: ${admin.address}`);

  const CredentialRegistry =
    await hre.ethers.getContractFactory("CredentialRegistry");

  const registry = await CredentialRegistry.deploy(admin.address);
  await registry.waitForDeployment();

  const address = await registry.getAddress();

  // Grant ISSUER_ROLE to the deployer/admin so the backend
  // can register and revoke credentials during local development.
  const issuerRole = await registry.ISSUER_ROLE();

  const roleTx = await registry.grantRole(issuerRole, admin.address);
  await roleTx.wait();

  console.log(`ISSUER_ROLE granted to: ${admin.address}`);
  console.log(`CredentialRegistry deployed to: ${address}`);

  // Write deployment info for the backend service to consume.
  const artifact = await hre.artifacts.readArtifact("CredentialRegistry");

  const deploymentInfo = {
    network: hre.network.name,
    address,
    admin: admin.address,
    issuer: admin.address,
    issuerRole,
    abi: artifact.abi,
    deployedAt: new Date().toISOString()
  };

  const outDir = path.join(__dirname, "..", "deployments");

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir);
  }

  const outFile = path.join(
    outDir,
    `${hre.network.name}-deployment.json`
  );

  fs.writeFileSync(
    outFile,
    JSON.stringify(deploymentInfo, null, 2)
  );

  console.log(`Deployment info written to: ${outFile}`);

  console.log(
    "\nCopy this address into blockchain/.env (CONTRACT_ADDRESS) and into " +
      "backend/blockchain-service/.env (CONTRACT_ADDRESS)."
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
}); 