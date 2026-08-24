"""
Thin wrapper around web3.py for talking to CredentialRegistry.sol.

This is the Python-backend equivalent of the ethers.js integration the spec
recommends for a JS backend — same responsibilities (sign + send registration
and revocation transactions, read verification data), different library
because the rest of this service is Python.
"""
from functools import lru_cache

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.config import Settings, get_settings, load_contract_abi


class BlockchainClient:
    def __init__(self, settings: Settings):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        # Harmless on standard chains; required on some PoA testnets. Kept in
        # so this client also works unmodified if the team later deploys to
        # a PoA testnet.
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        address, abi = load_contract_abi(settings)
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

        self._account = None
        if settings.issuer_private_key:
            self._account = self.w3.eth.account.from_key(settings.issuer_private_key)

    @property
    def issuer_address(self) -> str | None:
        return self._account.address if self._account else None

    @staticmethod
    def hex_hash_to_bytes32(hex_hash: str) -> bytes:
        """Convert a '0x...'-prefixed 64-char hex SHA-256 digest to bytes32."""
        clean = hex_hash[2:] if hex_hash.startswith("0x") else hex_hash
        if len(clean) != 64:
            raise ValueError("Expected a 32-byte (64 hex char) hash")
        return bytes.fromhex(clean)

    def _send(self, fn):
        if not self._account:
            raise RuntimeError(
                "ISSUER_PRIVATE_KEY is not configured — this service cannot "
                "sign write transactions. Set it in .env for local dev."
            )
        tx = fn.build_transaction(
            {
                "from": self._account.address,
                "nonce": self.w3.eth.get_transaction_count(self._account.address),
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, private_key=self._account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    def register_credential(self, credential_id: str, hex_hash: str):
        hash_bytes = self.hex_hash_to_bytes32(hex_hash)
        fn = self.contract.functions.registerCredential(credential_id, hash_bytes)
        return self._send(fn)

    def revoke_credential(self, credential_id: str):
        fn = self.contract.functions.revokeCredential(credential_id)
        return self._send(fn)

    def verify_credential(self, credential_id: str, hex_hash: str) -> bool:
        hash_bytes = self.hex_hash_to_bytes32(hex_hash)
        return self.contract.functions.verifyCredential(credential_id, hash_bytes).call()

    def get_credential(self, credential_id: str) -> dict | None:
        result = self.contract.functions.getCredential(credential_id).call()
        credential_hash, issuer, issued_at, revoked, exists = result
        if not exists:
            return None
        return {
            "credential_hash": "0x" + credential_hash.hex(),
            "issuer": issuer,
            "issued_at": issued_at,
            "revoked": revoked,
        }


@lru_cache
def get_blockchain_client() -> BlockchainClient:
    return BlockchainClient(get_settings())
