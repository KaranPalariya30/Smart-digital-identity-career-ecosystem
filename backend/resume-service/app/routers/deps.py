"""Shared helpers for the routers."""
from fastapi import HTTPException, UploadFile

from ..config import settings
from ..core.pdf_reader import ResumeParseError, clean_pasted_text, extract_text_from_pdf_bytes


async def read_resume(resume_file: UploadFile | None, resume_text: str | None) -> str:
    """Accept either a PDF upload or pasted text and return plain text."""
    try:
        if resume_file is not None and resume_file.filename:
            data = await resume_file.read(settings.max_upload_bytes + 1)
            if len(data) > settings.max_upload_bytes:
                raise HTTPException(413, f"File too large (max {settings.max_upload_bytes // 1024 // 1024} MB).")
            return extract_text_from_pdf_bytes(data)
        return clean_pasted_text(resume_text or "")
    except ResumeParseError as exc:
        raise HTTPException(400, str(exc)) from exc
