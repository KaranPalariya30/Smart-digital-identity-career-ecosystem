from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class Credential(Base):
    __tablename__ = "credentials"

    credential_id = Column(String(64), primary_key=True)
    # The auth-service user id (an integer there, stored as text here so the
    # two services never have to agree on a numeric type).
    user_id = Column(String(64), nullable=False, index=True)
    certificate_name = Column(String(255), nullable=False)
    certificate_type = Column(String(100))
    # Comma-separated canonical skills this credential verifies, e.g.
    # "python,react". Feeds the resume service's verified_skills.
    skills = Column(String(500))
    file_path = Column(String(500))
    document_hash = Column(String(66), nullable=False)
    blockchain_tx_hash = Column(String(66))
    blockchain_network = Column(String(50), nullable=False, default="localhost")
    contract_address = Column(String(42), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    verification_status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("verification_status IN ('active', 'revoked')", name="status_check"),
    )

    @property
    def skill_list(self) -> list[str]:
        return [s for s in (self.skills or "").split(",") if s]


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def init_db() -> None:
    """Create the table if it does not exist (no-op when a migration already did)."""
    Base.metadata.create_all(bind=get_engine())


def get_db():
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
