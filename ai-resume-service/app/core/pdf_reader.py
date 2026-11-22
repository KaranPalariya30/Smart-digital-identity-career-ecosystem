"""PDF -> text, entirely in memory (no temp files, so concurrent uploads can't collide)."""
import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..config import settings


class ResumeParseError(ValueError):
    """Raised when an uploaded resume cannot be turned into usable text."""


def extract_text_from_pdf_bytes(data: bytes) -> str:
    if not data:
        raise ResumeParseError("Uploaded file is empty.")
    if not data.lstrip()[:5] == b"%PDF-":          # magic bytes, not just file extension
        raise ResumeParseError("File is not a valid PDF.")

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ResumeParseError("Password-protected PDFs are not supported.")
        if len(reader.pages) > settings.max_pdf_pages:
            raise ResumeParseError(
                f"PDF has {len(reader.pages)} pages; maximum is {settings.max_pdf_pages}."
            )
        pages = [(page.extract_text() or "") for page in reader.pages]
    except ResumeParseError:
        raise
    except (PdfReadError, ValueError, KeyError) as exc:
        raise ResumeParseError(f"Could not read PDF: {exc}") from exc

    text = "\n".join(pages).strip()
    if not text:
        raise ResumeParseError(
            "No text found in this PDF. It may be a scanned image; upload a text-based PDF."
        )
    return text


def clean_pasted_text(raw: str) -> str:
    if not raw or not raw.strip():
        raise ResumeParseError("No resume text provided.")
    return raw.strip()
