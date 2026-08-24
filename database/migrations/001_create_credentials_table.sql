-- Off-chain application metadata for blockchain-verified credentials.
--
-- The blockchain (CredentialRegistry.sol) is the tamper-resistant source of
-- truth for credentialId / credentialHash / issuer / issuedAt / revoked.
-- This table stores everything the app needs beyond that, WITHOUT
-- duplicating sensitive data on-chain. No certificate files or PII columns
-- belong here either — file_path/storage_reference should point at storage
-- your existing auth/user services already govern access to.

CREATE TABLE IF NOT EXISTS credentials (
    credential_id           VARCHAR(64) PRIMARY KEY,
    user_id                 UUID NOT NULL,
    certificate_name        VARCHAR(255) NOT NULL,
    certificate_type        VARCHAR(100),
    file_path                VARCHAR(500),
    document_hash            CHAR(66) NOT NULL,        -- '0x' + 64 hex chars
    blockchain_tx_hash       CHAR(66),
    blockchain_network       VARCHAR(50) NOT NULL DEFAULT 'localhost',
    contract_address          VARCHAR(42) NOT NULL,
    issued_at                 TIMESTAMPTZ NOT NULL,
    verification_status       VARCHAR(20) NOT NULL DEFAULT 'active'
                               CHECK (verification_status IN ('active', 'revoked')),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credentials_user_id ON credentials (user_id);
CREATE INDEX IF NOT EXISTS idx_credentials_status ON credentials (verification_status);
