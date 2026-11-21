from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.routers import credentials

app = FastAPI(
    title="Blockchain Credential Service",
    description=(
        "Blockchain-backed credential registration, verification, and "
        "revocation for the Smart Digital Identity and Career Ecosystem."
    ),
    version="1.0.0",
)

app.include_router(credentials.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
VERIFY_PAGE = STATIC_DIR / "verify-demo.html"


@app.get("/verify/{credential_id}", include_in_schema=False)
def verification_page(credential_id: str):
    return FileResponse(VERIFY_PAGE)


@app.get("/health")
def health():
    return {"status": "ok"}
