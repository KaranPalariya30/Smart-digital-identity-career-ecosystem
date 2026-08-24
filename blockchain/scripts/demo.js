const hre = require("hardhat");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

// Full end-to-end demonstration for a project presentation:
//   1. Create a sample certificate
//   2. Hash it (SHA-256)
//   3. Register it on-chain
//   4. Verify it (should pass)
//   5. Tamper with it, re-hash, verify again (should fail)
//   6. Revoke it, verify again (should show revoked)

function sha256File(filePath) {
  const data = fs.readFileSync(filePath);
  return "0x" + crypto.createHash("sha256").update(data).digest("hex");
}

async function main() {
  const deploymentFile = path.join(
    __dirname,
    "..",
    "deployments",
    `${hre.network.name}-deployment.json`
  );
  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`No deployment found. Run "npm run deploy:localhost" first.`);
  }
  const { address } = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));

  const [admin, issuer] = await hre.ethers.getSigners();
  const registry = await hre.ethers.getContractAt("CredentialRegistry", address);

  // Ensure the demo issuer is authorized (idempotent-ish for repeat demo runs)
  const hasIssuerRole = await registry.hasRole(await registry.ISSUER_ROLE(), issuer.address);
  if (!hasIssuerRole) {
    console.log(`Authorizing demo issuer ${issuer.address}...`);
    await (await registry.connect(admin).authorizeIssuer(issuer.address)).wait();
  }

  // Step 1-2: sample certificate + hash
  const demoDir = path.join(__dirname, "..", "demo-artifacts");
  if (!fs.existsSync(demoDir)) fs.mkdirSync(demoDir);
  const certPath = path.join(demoDir, "sample-certificate.txt");
  fs.writeFileSync(
    certPath,
    "CERTIFICATE OF COMPLETION\nName: Demo Student\nCourse: Blockchain 101\nDate: 2026-08-22\n"
  );
  const hashA = sha256File(certPath);
  console.log(`\n[1] Sample certificate created at ${certPath}`);
  console.log(`[2] SHA-256 hash: ${hashA}`);

  // Step 3: register on-chain
  const credentialId = `CRED-${Date.now()}`;
  console.log(`\n[3] Registering credential "${credentialId}"...`);
  const registerTx = await registry.connect(issuer).registerCredential(credentialId, hashA);
  const registerReceipt = await registerTx.wait();
  console.log(`    Tx hash: ${registerReceipt.hash}`);
  console.log(`    Verification URL: http://localhost:5173/verify/${credentialId}`);

  // Step 4: verify (should pass)
  let valid = await registry.verifyCredential(credentialId, hashA);
  console.log(`\n[4] Verify with original hash -> ${valid ? "VERIFIED" : "INVALID"}`);

  // Step 5: tamper + re-hash + verify (should fail)
  fs.appendFileSync(certPath, "\n-- tampered line added --\n");
  const hashB = sha256File(certPath);
  console.log(`\n[5] Certificate modified. New hash: ${hashB}`);
  valid = await registry.verifyCredential(credentialId, hashB);
  console.log(`    Verify with new hash -> ${valid ? "VERIFIED" : "INVALID / TAMPERED"}`);

  // Step 6: revoke + verify (should show revoked)
  console.log(`\n[6] Revoking credential...`);
  await (await registry.connect(issuer).revokeCredential(credentialId)).wait();
  valid = await registry.verifyCredential(credentialId, hashA);
  const details = await registry.getCredential(credentialId);
  console.log(`    Verify with original hash after revocation -> ${valid ? "VERIFIED" : "REVOKED / INVALID"}`);
  console.log(`    On-chain record: revoked=${details.revoked}, issuer=${details.issuer}`);

  console.log("\nDemo complete.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
