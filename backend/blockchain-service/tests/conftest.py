"""Test setup: SQLite, a fake chain, and tokens signed like auth-service signs them."""
import os
import tempfile
import time

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars"
os.environ["SERVICE_API_TOKEN"] = "test-service-token"
os.environ["ISSUER_ROLES"] = "ADMIN"
os.environ["FRONTEND_VERIFY_BASE_URL"] = "http://localhost:5173/verify"

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.blockchain_client import get_blockchain_client  # noqa: E402
from app.main import app  # noqa: E402

SECRET = os.environ["AUTH_SECRET_KEY"]


class _Receipt(dict):
    pass


class FakeContract:
    address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"


class FakeChain:
    """Same surface as BlockchainClient, but keeps the 'ledger' in a dict."""

    contract = FakeContract()

    def __init__(self):
        self.ledger: dict[str, dict] = {}
        self._n = 0

    def _receipt(self):
        self._n += 1
        return {"transactionHash": bytes([self._n]) * 32}

    def register_credential(self, credential_id, hex_hash):
        self.ledger[credential_id] = {
            "credential_hash": hex_hash,
            "issuer": "0xIssuerAccount",
            "issued_at": int(time.time()),
            "revoked": False,
        }
        return self._receipt()

    def revoke_credential(self, credential_id):
        self.ledger[credential_id]["revoked"] = True
        return self._receipt()

    def get_credential(self, credential_id):
        return self.ledger.get(credential_id)


def make_token(sub="7", role="STUDENT", purpose="access", secret=SECRET, exp_in=3600):
    return jwt.encode(
        {"sub": sub, "role": role, "token_version": 0, "purpose": purpose, "exp": int(time.time()) + exp_in},
        secret,
        algorithm="HS256",
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def chain():
    fake = FakeChain()
    app.dependency_overrides[get_blockchain_client] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture()
def client(chain):
    from app.database import Base, get_engine

    with TestClient(app) as c:       # startup creates the tables
        Base.metadata.drop_all(bind=get_engine())
        Base.metadata.create_all(bind=get_engine())   # every test starts empty
        yield c
