from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url.replace("postgresql://", "postgresql+psycopg2://"))
    return _engine


class _LazyEngine:
    def __getattr__(self, name):
        return getattr(get_engine(), name)


engine = _LazyEngine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal(bind=get_engine())
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=get_engine())
