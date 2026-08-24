import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class Credential(Base):
    __tablename__ = "credentials"

    credential_id = Column(String(64), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    certificate_name = Column(String(255), nullable=False)
    certificate_type = Column(String(100))
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


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_db():
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
