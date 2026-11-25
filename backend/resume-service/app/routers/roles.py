from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..auth import require_user
from ..core.roles import get_role, load_roles, rank_roles
from ..schemas import RecommendResponse, RecommendTextRequest, RoleDetail, RoleSummary
from ..services.analyzer import extract_resume_skills
from .deps import read_resume

router = APIRouter(prefix="/api/v1/roles", tags=["roles"], dependencies=[Depends(require_user)])


def _recommend(text: str, top_k: int) -> dict:
    skills = set(extract_resume_skills(text))
    return {"detected_skills": sorted(skills), "recommendations": rank_roles(skills, top_k)}


@router.get("", response_model=list[RoleSummary], summary="List available target roles")
async def list_roles():
    return [RoleSummary(id=r.id, title=r.title, description=r.description) for r in load_roles().values()]


@router.get("/{role_id}", response_model=RoleDetail)
async def role_detail(role_id: str):
    role = get_role(role_id)
    if role is None:
        raise HTTPException(404, f"Unknown role '{role_id}'")
    return RoleDetail(id=role.id, title=role.title, description=role.description,
                      required=list(role.required), preferred=list(role.preferred))


@router.post("/recommend", response_model=RecommendResponse,
             summary="No JD needed: which roles fit this resume best? (multipart form)")
async def recommend_form(resume_file: UploadFile | None = File(None),
                         resume_text: str | None = Form(None),
                         top_k: int = Form(3)):
    text = await read_resume(resume_file, resume_text)
    return await run_in_threadpool(_recommend, text, max(1, min(top_k, 9)))


@router.post("/recommend/text", response_model=RecommendResponse, summary="Same, JSON body")
async def recommend_json(body: RecommendTextRequest):
    return await run_in_threadpool(_recommend, body.resume_text.strip(), body.top_k)
