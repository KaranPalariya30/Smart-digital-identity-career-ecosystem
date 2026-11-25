"""Central settings. Every tunable number lives here, not scattered in the code."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    # --- upload limits -------------------------------------------------
    max_upload_bytes: int = 5 * 1024 * 1024
    max_pdf_pages: int = 15
    min_jd_chars: int = 50

    # --- scoring (tune these against a small labelled set) ----------------
    # Resume-vs-JD cosine similarity rarely goes above ~0.45 even for a
    # strong match, so we divide by this ceiling instead of the old
    # arbitrary "* 250". Re-fit it once you have labelled examples.
    cosine_ceiling: float = 0.45
    w_skill: float = 0.60          # weight of weighted-skill coverage
    w_text: float = 0.40           # weight of text similarity component
    w_cosine_in_text: float = 0.70
    w_coverage_in_text: float = 0.30
    scoring_version: str = "2.0.0"

    # --- data files ----------------------------------------------------
    roles_path: Path = ROOT / "data" / "roles.json"
    idf_path: Path = ROOT / "data" / "idf_corpus.json"   # optional, see scripts/build_idf.py

    # --- auth (JWTs issued by backend/auth-service; JWT_SECRET == its SECRET_KEY) ----
    auth_enabled: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Browser origins allowed to call this API (the React app in development).
    cors_origins: tuple = tuple(
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if o.strip()
    )


settings = Settings()
