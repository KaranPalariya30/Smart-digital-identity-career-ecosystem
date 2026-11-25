from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import init_db
from app.routers import credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Blockchain Credential Service",
    description=(
        "Blockchain-backed credential registration, verification, and "
        "revocation for the Smart Digital Identity and Career Ecosystem."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
