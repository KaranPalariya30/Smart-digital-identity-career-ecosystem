// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title CredentialRegistry
/// @notice Stores tamper-resistant, non-PII verification metadata for academic/
///         professional credentials issued through the Smart Digital Identity
///         and Career Ecosystem platform.
/// @dev Only a SHA-256 hash of the original credential document is stored
///      on-chain — never the document itself, and never PII. See
///      docs/blockchain/architecture.md for the full rationale.
contract CredentialRegistry is AccessControl {
    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");

    struct Credential {
        bytes32 credentialHash; // SHA-256 digest of the off-chain document
        address issuer;         // wallet that registered this credential
        uint256 issuedAt;       // block timestamp at registration
        bool revoked;           // revocation flag
        bool exists;            // existence flag (distinguishes from default struct)
    }

    // credentialId => Credential
    mapping(string => Credential) private credentials;

    event CredentialRegistered(
        string indexed credentialId,
        bytes32 credentialHash,
        address indexed issuer,
        uint256 issuedAt
    );

    event CredentialRevoked(
        string indexed credentialId,
        address indexed revokedBy,
        uint256 revokedAt
    );

    event IssuerAuthorized(address indexed issuer, address indexed authorizedBy);
    event IssuerRevoked(address indexed issuer, address indexed revokedBy);

    /// @param admin Address granted DEFAULT_ADMIN_ROLE at deployment. This
    ///        address can authorize/revoke issuers but cannot itself register
    ///        or revoke credentials unless it is also granted ISSUER_ROLE.
    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    // ---------------------------------------------------------------------
    // Issuer management (admin only)
    // ---------------------------------------------------------------------

    /// @notice Authorize a new issuer. Admin-only.
    function authorizeIssuer(address issuer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(ISSUER_ROLE, issuer);
        emit IssuerAuthorized(issuer, msg.sender);
    }

    /// @notice Revoke an issuer's authorization. Admin-only.
    function revokeIssuer(address issuer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(ISSUER_ROLE, issuer);
        emit IssuerRevoked(issuer, msg.sender);
    }

    // ---------------------------------------------------------------------
    // Credential lifecycle (authorized issuer only)
    // ---------------------------------------------------------------------

    /// @notice Register a new credential. Reverts on duplicate IDs.
    /// @param credentialId Unique, application-generated identifier (e.g. UUID).
    /// @param credentialHash SHA-256 digest of the off-chain credential document.
    function registerCredential(string calldata credentialId, bytes32 credentialHash)
        external
        onlyRole(ISSUER_ROLE)
    {
        require(bytes(credentialId).length > 0, "CredentialRegistry: empty credentialId");
        require(credentialHash != bytes32(0), "CredentialRegistry: empty hash");
        require(!credentials[credentialId].exists, "CredentialRegistry: credential already exists");

        credentials[credentialId] = Credential({
            credentialHash: credentialHash,
            issuer: msg.sender,
            issuedAt: block.timestamp,
            revoked: false,
            exists: true
        });

        emit CredentialRegistered(credentialId, credentialHash, msg.sender, block.timestamp);
    }

    /// @notice Revoke an existing credential. Only the original issuer or an
    ///         admin may revoke it.
    function revokeCredential(string calldata credentialId) external {
        Credential storage cred = credentials[credentialId];
        require(cred.exists, "CredentialRegistry: credential not found");
        require(
            hasRole(ISSUER_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "CredentialRegistry: caller is not an authorized issuer or admin"
        );
        require(!cred.revoked, "CredentialRegistry: already revoked");

        cred.revoked = true;
        emit CredentialRevoked(credentialId, msg.sender, block.timestamp);
    }

    // ---------------------------------------------------------------------
    // Public verification (no auth required)
    // ---------------------------------------------------------------------

    /// @notice Verify a credential by ID and recomputed hash.
    /// @return valid True iff the credential exists, the hash matches, and it
    ///         is not revoked.
    function verifyCredential(string calldata credentialId, bytes32 credentialHash)
        external
        view
        returns (bool valid)
    {
        Credential storage cred = credentials[credentialId];
        if (!cred.exists) return false;
        if (cred.credentialHash != credentialHash) return false;
        if (cred.revoked) return false;
        return true;
    }

    /// @notice Fetch public verification metadata for a credential.
    function getCredential(string calldata credentialId)
        external
        view
        returns (
            bytes32 credentialHash,
            address issuer,
            uint256 issuedAt,
            bool revoked,
            bool exists
        )
    {
        Credential storage cred = credentials[credentialId];
        return (cred.credentialHash, cred.issuer, cred.issuedAt, cred.revoked, cred.exists);
    }
}
