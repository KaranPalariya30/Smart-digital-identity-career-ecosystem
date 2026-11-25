import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth import Principal, require_issuer, require_user
from app.blockchain_client import BlockchainClient, get_blockchain_client
from app.config import Settings, get_settings
from app.database import Credential, get_db
from app.hashing import sha256_bytes
from app.qr import build_verification_url, generate_qr_png_base64
from app.schemas import (
    CredentialDetailResponse,
    CredentialRegisterResponse,
    MyCredential,
    RevokeResponse,
    VerifyResult,
)

# Access rules:
#   * issue / revoke  -> an issuer (auth-service role in ISSUER_ROLES, ADMIN by
#                        default) or the static SERVICE_API_TOKEN
#   * /mine           -> any logged-in user, own credentials only
#   * detail / verify -> public, by design (employers have no account)
router = APIRouter(prefix="/api/blockchain/credentials", tags=["blockchain-credentials"])

_USER_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


def _clean_skills(raw: str | None) -> str | None:
    """'Python, React ,python' -> 'python,react' (lowercase, unique, ordered)."""
    if not raw:
        return None
    seen: list[str] = []
    for part in raw.split(","):
        skill = part.strip().lower()
        if skill and skill not in seen:
            seen.append(skill)
    joined = ",".join(seen)
    if len(joined) > 500:
        raise HTTPException(status_code=422, detail="Too many skills (max 500 characters)")
    return joined or None


def _chain_write(fn, *args):
    """Run a signing call; turn 'chain down / no signer key' into a clear 503 instead of a bare 500."""
    try:
        return fn(*args)
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Blockchain unavailable: {exc}") from exc


def _tx_hex(receipt) -> str:
    tx_hash = receipt["transactionHash"].hex()
    return tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash


@router.post(
    "",
    response_model=CredentialRegisterResponse,
    status_code=201,
    dependencies=[Depends(require_issuer)],
)
async def register_credential(
    file: UploadFile,
    user_id: str = Query(..., description="auth-service id of the student who owns this credential"),
    certificate_name: str = Query(..., min_length=1, max_length=255),
    certificate_type: str | None = Query(None, max_length=100),
    skills: str | None = Query(None, description="comma-separated skills this credential verifies"),
    db: Session = Depends(get_db),
    client: BlockchainClient = Depends(get_blockchain_client),
    settings: Settings = Depends(get_settings),
):
    """Register a new credential.

    The uploaded file is hashed here and then discarded from memory; only the
    hash goes on-chain, and only a storage reference (not the raw bytes) is
    expected to persist off-chain via file_path.
    """
    if not _USER_ID.match(user_id):
        raise HTTPException(status_code=422, detail="user_id may use letters, digits and _ . : - (max 64)")
    skill_csv = _clean_skills(skills)

    contents = await file.read()
    document_hash = sha256_bytes(contents)
    credential_id = f"CRED-{uuid.uuid4().hex[:12].upper()}"

    receipt = _chain_write(client.register_credential, credential_id, document_hash)
    tx_hash = _tx_hex(receipt)

    row = Credential(
        credential_id=credential_id,
        user_id=user_id,
        certificate_name=certificate_name,
        certificate_type=certificate_type,
        skills=skill_csv,
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
        skills=row.skill_list,
    )


# NOTE: declared before "/{credential_id}" so "mine" is not read as an id.
@router.get("/mine", response_model=list[MyCredential])
def my_credentials(
    principal: Principal = Depends(require_user),
    db: Session = Depends(get_db),
):
    """The logged-in user's own credentials (active and revoked)."""
    rows = (
        db.query(Credential)
        .filter(Credential.user_id == principal.user_id)
        .order_by(Credential.issued_at.desc())
        .all()
    )
    return [
        MyCredential(
            credential_id=r.credential_id,
            certificate_name=r.certificate_name,
            certificate_type=r.certificate_type,
            issued_at=r.issued_at,
            verification_status=r.verification_status,
            skills=r.skill_list,
        )
        for r in rows
    ]


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
        document_hash=row.document_hash,
        skills=row.skill_list,
    )


@router.post("/{credential_id}/verify", response_model=VerifyResult)
async def verify_credential(
    credential_id: str,
    file: UploadFile | str | None = File(default=None),
    db: Session = Depends(get_db),
    client: BlockchainClient = Depends(get_blockchain_client),
):
    """Public verification endpoint."""

    row = db.get(Credential, credential_id)

    if not row:
        return VerifyResult(credential_id=credential_id, status="NOT_FOUND")

    # Check whether the credential belongs to the current deployment.
    if row.contract_address.lower() != client.contract.address.lower():
        return VerifyResult(credential_id=credential_id, status="DEPLOYMENT_MISMATCH")

    # Hash the uploaded document if one was provided, else trust the stored hash.
    if file is not None and not isinstance(file, str):
        contents = await file.read()
        check_hash = sha256_bytes(contents)
    else:
        check_hash = row.document_hash

    on_chain = client.get_credential(credential_id)

    if on_chain is None:
        return VerifyResult(credential_id=credential_id, status="NOT_FOUND")

    if on_chain["credential_hash"].lower() != check_hash.lower():
        return VerifyResult(credential_id=credential_id, status="INVALID")

    if on_chain["revoked"]:
        return VerifyResult(credential_id=credential_id, status="REVOKED", issuer=on_chain["issuer"])

    return VerifyResult(
        credential_id=credential_id,
        status="VERIFIED",
        issuer=on_chain["issuer"],
        issued_at=row.issued_at,
    )


@router.post(
    "/{credential_id}/revoke",
    response_model=RevokeResponse,
    dependencies=[Depends(require_issuer)],
)
def revoke_credential(
    credential_id: str,
    db: Session = Depends(get_db),
    client: BlockchainClient = Depends(get_blockchain_client),
):
    """Revoke a credential (issuer only)."""
    row = db.get(Credential, credential_id)
    if not row:
        raise HTTPException(status_code=404, detail="Credential not found")
    if row.verification_status == "revoked":
        raise HTTPException(status_code=409, detail="Credential already revoked")

    receipt = _chain_write(client.revoke_credential, credential_id)
    tx_hash = _tx_hex(receipt)

    row.verification_status = "revoked"
    row.blockchain_tx_hash = tx_hash
    db.commit()

    return RevokeResponse(
        credential_id=credential_id,
        verification_status="revoked",
        blockchain_tx_hash=tx_hash,
    )
