import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CredentialRegisterResponse(BaseModel):
    credential_id: str
    document_hash: str
    blockchain_tx_hash: str
    contract_address: str
    verification_url: str
    qr_code_base64: str


class CredentialDetailResponse(BaseModel):
    credential_id: str
    certificate_name: str
    certificate_type: Optional[str]
    issuer: str
    issued_at: datetime
    verification_status: Literal["active", "revoked"]
    blockchain_tx_hash: Optional[str]
    contract_address: str


class VerifyResult(BaseModel):
    credential_id: str
    status: Literal["VERIFIED", "REVOKED", "INVALID", "NOT_FOUND"]
    issuer: Optional[str] = None
    issued_at: Optional[datetime] = None


class RevokeResponse(BaseModel):
    credential_id: str
    verification_status: Literal["revoked"]
    blockchain_tx_hash: str
