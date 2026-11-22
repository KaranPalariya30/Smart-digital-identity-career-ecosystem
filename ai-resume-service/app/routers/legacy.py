"""
Backward-compatible POST /analyze with the OLD v1 response shape, so the
existing frontend/app.js keeps working while the team migrates to /api/v1.
Delete this file once the frontend uses the new contract.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from ..core.jd_resolver import resolve_jd
from ..services.analyzer import analyze
from .deps import read_resume

router = APIRouter(tags=["legacy"])


@router.post("/analyze", include_in_schema=True, summary="[legacy] v1-compatible analyze")
async def legacy_analyze(request: Request):
    if request.headers.get("content-type", "").startswith("multipart/"):
        form = await request.form()
        resume_file, resume_text, jd_text = form.get("resume_file"), None, form.get("jd_text", "")
    elif "json" in request.headers.get("content-type", ""):
        data = await request.json()
        resume_file, resume_text, jd_text = None, data.get("resume_text", ""), data.get("jd_text", "")
    else:
        raise HTTPException(400, "Send either a PDF file or JSON with resume_text")

    text = await read_resume(resume_file, resume_text)
    jd = resolve_jd("jd", jd_text, None)
    r = await run_in_threadpool(analyze, text, jd, mode="jd")

    return {
        "success": True,
        "score": {"overall": r.score.overall, "grade": r.score.grade,
                  "cosine_similarity": r.score.cosine_similarity,
                  "keyword_coverage": r.score.keyword_coverage, "summary": r.score.summary},
        "keywords": r.keywords.model_dump(),
        "skills": {"matched": [s.name for s in r.skills.matched],
                   "missing": [s.name for s in r.skills.missing],
                   "bonus": [s.name for s in r.skills.bonus],
                   "match_percentage": r.skills.match_percentage,
                   "resume_by_category": r.skills.resume_by_category,
                   "jd_by_category": r.skills.jd_by_category},
        "feedback": r.feedback.model_dump(),
    }
