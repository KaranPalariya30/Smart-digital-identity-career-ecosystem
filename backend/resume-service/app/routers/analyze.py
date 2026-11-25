from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..auth import require_user
from ..core.jd_resolver import resolve_jd
from ..schemas import AnalysisResponse, AnalyzeTextRequest
from ..services.analyzer import analyze
from .deps import read_resume

router = APIRouter(prefix="/api/v1", tags=["analysis"], dependencies=[Depends(require_user)])


def _split(csv: str | None) -> list[str]:
    return [s.strip() for s in (csv or "").split(",") if s.strip()]


@router.post("/analyze", response_model=AnalysisResponse,
             summary="Analyze a resume (PDF upload or pasted text) - multipart form")
async def analyze_form(
    resume_file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
    jd_text: str | None = Form(None),
    target_role: str | None = Form(None),
    mode: str = Form("auto"),
    verified_skills: str | None = Form(None, description="comma-separated"),
):
    text = await read_resume(resume_file, resume_text)
    jd = resolve_jd(mode, jd_text, target_role)
    return await run_in_threadpool(analyze, text, jd, mode=mode, verified_skills=_split(verified_skills))


@router.post("/analyze/text", response_model=AnalysisResponse,
             summary="Analyze a resume - JSON body (for service-to-service calls)")
async def analyze_json(body: AnalyzeTextRequest):
    jd = resolve_jd(body.mode, body.jd_text, body.target_role)
    return await run_in_threadpool(analyze, body.resume_text.strip(), jd,
                                   mode=body.mode, verified_skills=body.verified_skills)
