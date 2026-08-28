from fastapi import FastAPI

from app.database.database import Base, engine
from app.database import models
from app.routes.auth import router as auth_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Digital Identity - Authentication Service",
    version="1.0.0"
)


app.include_router(auth_router)


@app.get("/")
def health_check():
    return {
        "message": "Authentication service is running"
    }