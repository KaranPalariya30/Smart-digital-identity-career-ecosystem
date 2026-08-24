import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.blockchain_client import BlockchainClient, get_blockchain_client
from app.config import Settings, get_settings
from app.database import Credential, get_db
from app.hashing import sha256_bytes
from app.qr import build_verification_url, generate_qr_png_base64
from app.schemas import (
    CredentialDetailResponse,
    CredentialRegisterResponse,
    RevokeResponse,
    VerifyResult,
)

# NOTE on auth: this router intentionally does not implement its own
# authentication. Registration/revocation routes are meant to sit behind
# whatever the team's existing auth-service already provides (e.g. an
# `Depends(require_role("issuer"))` guard) — wire that in here once
# auth-service exists. Verification is deliberately public, per the spec.
router = APIRouter(prefix="/api/blockchain/credentials", tags=["blockchain-credentials"])


@router.post("", response_model=CredentialRegisterResponse, status_code=201)
async def register_credential(
    file: UploadFile,
    user_id: uuid.UUID,
    certificate_name: str,
    certificate_type: str | None = None,
    db: Session = Depends(get_db),
    client: BlockchainClient = Depends(get_blockchain_client),
    settings: Settings = Depends(get_settings),
):
    """Register a new credential.

    Only an authorized issuer should be able to call this in production —
    see the auth note above. The uploaded file is hashed here and then
    discarded from memory; only the hash goes on-chain, and only a storage
    reference (not the raw bytes) is expected to persist off-chain via
    file_path, wired to whatever object storage the team already uses.
    """
    contents = await file.read()
    document_hash = sha256_bytes(contents)
    credential_id = f"CRED-{uuid.uuid4().hex[:12].upper()}"

    receipt = client.register_credential(credential_id, document_hash)
    tx_hash = receipt["transactionHash"].hex()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    row = Credential(
        credential_id=credential_id,
        user_id=user_id,
        certificate_name=certificate_name,
        certificate_type=certificate_type,
        file_path=None,  # wire to real object storage when it exists
        document_hash=document_hash,
        blockchain_tx_hash=tx_hash,
        blockchain_network="localhost",
        contract_address=client.contract.address,
        issued_at=datetime.now(timezone.utc),
        verification_status="active",
    )
    db.add(row)
    db.commit()

    verify_url = build_verification_url(settings, credential_id)
    qr_b64 = generate_qr_png_base64(verify_url)

    return CredentialRegisterResponse(
        credential_id=credential_id,
        document_hash=document_hash,
        blockchain_tx_hash=tx_hash,
        contract_address=client.contract.address,
        verification_url=verify_url,
        qr_code_base64=qr_b64,
    )


@router.get("/{credential_id}", response_model=CredentialDetailResponse)
def get_credential(credential_id: str, db: Session = Depends(get_db)):
    row = db.get(Credential, credential_id)
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")

    return CredentialDetailResponse(
        credential_id=row.credential_id,
        certificate_name=row.certificate_name,
        certificate_type=row.certificate_type,
        issuer=row.contract_address,
        issued_at=row.issued_at,
        verification_status=row.verification_status,
        blockchain_tx_hash=row.blockchain_tx_hash,
        contract_address=row.contract_address,
    )


@router.post("/{credential_id}/verify", response_model=VerifyResult)
async def verify_credential(
    credential_id: str,
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    client: BlockchainClient = Depends(get_blockchain_client),
):
    """Public verification endpoint — no authentication required.

    If a file is supplied, its hash is recomputed and checked against the
    blockchain record (proves the specific document wasn't tampered with).
    If no file is supplied, verification falls back to the hash already on
    record in the database (useful for the QR-scan flow, where the verifier
    doesn't have the original document).
    """
    row = db.get(Credential, credential_id)
    if not row:
        return VerifyResult(credential_id=credential_id, status="NOT_FOUND")

    if file is not None:
        contents = await file.read()
        check_hash = sha256_bytes(contents)
    else:
        check_hash = row.document_hash

    on_chain = client.get_credential(credential_id)
    if on_chain is None:
        return VerifyResult(credential_id=credential_id, status="NOT_FOUND")

    if on_chain["credential_hash"] != check_hash:
        return VerifyResult(credential_id=credential_id, status="INVALID")

    if on_chain["revoked"]:
        return VerifyResult(
            credential_id=credential_id,
            status="REVOKED",
            issuer=on_chain["issuer"],
        )

    return VerifyResult(
        credential_id=credential_id,
        status="VERIFIED",
        issuer=on_chain["issuer"],
        issued_at=row.issued_at,
    )


@router.post("/{credential_id}/revoke", response_model=RevokeResponse)
def revoke_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    client: BlockchainClient = Depends(get_blockchain_client),
):
    """Revoke a credential. Only an authorized issuer/admin should be able to
    call this — see the auth note at the top of this file."""
    row = db.get(Credential, credential_id)
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")
    if row.verification_status == "revoked":
        raise HTTPException(status_code=409, detail="Credential already revoked")

    receipt = client.revoke_credential(credential_id)
    tx_hash = receipt["transactionHash"].hex()
    if not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    row.verification_status = "revoked"
    row.blockchain_tx_hash = tx_hash
    db.commit()

    return RevokeResponse(
        credential_id=credential_id,
        verification_status="revoked",
        blockchain_tx_hash=tx_hash,
    )
