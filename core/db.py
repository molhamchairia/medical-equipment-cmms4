import os
import tempfile
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
def _demo_enabled():
    value = os.environ.get("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    try:
        import streamlit as st
        value = str(st.secrets.get("DEMO_MODE", value)).strip().lower() in {"1", "true", "yes", "on"}
    except Exception:
        pass
    return value

if os.environ.get("CMMS_DB_PATH"):
    DB_PATH = Path(os.environ["CMMS_DB_PATH"]).expanduser().resolve()
elif _demo_enabled():
    DB_PATH = Path(tempfile.gettempdir()) / "cmms_demo.db"
else:
    DB_PATH = ROOT / "data" / "cmms.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(DB_PATH.as_uri(), connect_args={"check_same_thread": False, "timeout": 5}, future=True)

@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    cursor.close()

class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_db():
    from core import models  # noqa: F401
    Base.metadata.create_all(engine)
