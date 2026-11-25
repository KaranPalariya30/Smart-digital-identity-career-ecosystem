import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .core.jd_resolver import JDResolutionError, ModeNotAvailableError
from .core.roles import load_roles
from .core.text_cleaner import _nlp
from .routers import analyze, legacy, roles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("resume_ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _nlp()            # load spaCy once at startup instead of on the first request
    load_roles()
    log.info("Resume AI service ready (scoring %s)", settings.scoring_version)
    yield


app = FastAPI(
    title="Smart Digital Identity - Resume AI Service",
    version=settings.scoring_version,
    description="Resume analysis, role matching and skill-gap learning paths.",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(JDResolutionError)
async def _bad_jd(_: Request, exc: JDResolutionError):
    return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})


@app.exception_handler(ModeNotAvailableError)
async def _mode_unavailable(_: Request, exc: ModeNotAvailableError):
    return JSONResponse(status_code=501, content={"success": False, "error": str(exc)})


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "resume-ai", "version": settings.scoring_version}


app.include_router(analyze.router)
app.include_router(roles.router)
app.include_router(legacy.router)

# Optional: serve the old static frontend at /ui for local demos.
_frontend = Path(os.getenv("FRONTEND_DIR", settings.roles_path.parent.parent / "frontend"))
if _frontend.is_dir():
    app.mount("/ui", StaticFiles(directory=_frontend, html=True), name="ui")
