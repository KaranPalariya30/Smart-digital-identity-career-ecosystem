const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyUint } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

describe("CredentialRegistry", function () {
  let registry, admin, issuer, other, stranger;

  const CRED_ID = "CRED-001";
  const HASH_A = ethers.keccak256(ethers.toUtf8Bytes("original-certificate-bytes"));
  const HASH_B = ethers.keccak256(ethers.toUtf8Bytes("tampered-certificate-bytes"));

  beforeEach(async function () {
    [admin, issuer, other, stranger] = await ethers.getSigners();

    const CredentialRegistry = await ethers.getContractFactory("CredentialRegistry");
    registry = await CredentialRegistry.deploy(admin.address);
    await registry.waitForDeployment();

    await registry.connect(admin).authorizeIssuer(issuer.address);
  });

  // Test 1: Authorized issuer can register a credential.
  it("allows an authorized issuer to register a credential", async function () {
    await expect(registry.connect(issuer).registerCredential(CRED_ID, HASH_A)).to.not.be.reverted;

    const cred = await registry.getCredential(CRED_ID);
    expect(cred.exists).to.equal(true);
    expect(cred.credentialHash).to.equal(HASH_A);
    expect(cred.issuer).to.equal(issuer.address);
    expect(cred.revoked).to.equal(false);
  });

  // Test 2: Unauthorized account cannot register a credential.
  it("reverts when an unauthorized account tries to register a credential", async function () {
    await expect(
      registry.connect(stranger).registerCredential(CRED_ID, HASH_A)
    ).to.be.revertedWithCustomError(registry, "AccessControlUnauthorizedAccount");
  });

  // Test 3: Duplicate credential IDs are rejected.
  it("rejects duplicate credential IDs", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    await expect(
      registry.connect(issuer).registerCredential(CRED_ID, HASH_B)
    ).to.be.revertedWith("CredentialRegistry: credential already exists");
  });

  // Test 4: Correct hash verifies successfully.
  it("verifies successfully with the correct hash", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    expect(await registry.verifyCredential(CRED_ID, HASH_A)).to.equal(true);
  });

  // Test 5: Incorrect hash fails verification.
  it("fails verification with an incorrect hash", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    expect(await registry.verifyCredential(CRED_ID, HASH_B)).to.equal(false);
  });

  // Test 6: Credential can be revoked.
  it("allows an authorized issuer to revoke a credential", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    await expect(registry.connect(issuer).revokeCredential(CRED_ID)).to.not.be.reverted;

    const cred = await registry.getCredential(CRED_ID);
    expect(cred.revoked).to.equal(true);
  });

  // Test 7: Revoked credential cannot be considered valid.
  it("treats a revoked credential as invalid even with the correct hash", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    await registry.connect(issuer).revokeCredential(CRED_ID);
    expect(await registry.verifyCredential(CRED_ID, HASH_A)).to.equal(false);
  });

  // Test 8: Unauthorized account cannot revoke a credential.
  it("reverts when an unauthorized account tries to revoke a credential", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    await expect(
      registry.connect(stranger).revokeCredential(CRED_ID)
    ).to.be.revertedWith("CredentialRegistry: caller is not an authorized issuer or admin");
  });

  // Test 9: CredentialRegistered event is emitted.
  it("emits CredentialRegistered on registration", async function () {
    await expect(registry.connect(issuer).registerCredential(CRED_ID, HASH_A))
      .to.emit(registry, "CredentialRegistered")
      .withArgs(CRED_ID, HASH_A, issuer.address, anyUint);
  });

  // Test 10: CredentialRevoked event is emitted.
  it("emits CredentialRevoked on revocation", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    await expect(registry.connect(issuer).revokeCredential(CRED_ID))
      .to.emit(registry, "CredentialRevoked")
      .withArgs(CRED_ID, issuer.address, anyUint);
  });

  // --- extra coverage beyond the required 10 ---

  it("returns not-found (exists=false) for an unknown credential", async function () {
    const cred = await registry.getCredential("does-not-exist");
    expect(cred.exists).to.equal(false);
    expect(await registry.verifyCredential("does-not-exist", HASH_A)).to.equal(false);
  });

  it("allows an admin (not just the original issuer) to revoke a credential", async function () {
    await registry.connect(issuer).registerCredential(CRED_ID, HASH_A);
    await expect(registry.connect(admin).revokeCredential(CRED_ID)).to.not.be.reverted;
  });

  it("prevents a revoked issuer from registering further credentials", async function () {
    await registry.connect(admin).revokeIssuer(issuer.address);
    await expect(
      registry.connect(issuer).registerCredential(CRED_ID, HASH_A)
    ).to.be.revertedWithCustomError(registry, "AccessControlUnauthorizedAccount");
  });
});
