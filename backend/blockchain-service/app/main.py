from fastapi import FastAPI

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


@app.get("/health")
def health():
    return {"status": "ok"}
