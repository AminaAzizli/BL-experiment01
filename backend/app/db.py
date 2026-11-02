from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def migrate_schema() -> None:
    session_columns = {
        column["name"] for column in inspect(engine).get_columns("sessions")
    }
    additions = {
        "actor_type": "VARCHAR(16) NOT NULL DEFAULT 'human'",
        "persona": "VARCHAR(64) NOT NULL DEFAULT 'human_participant'",
        "persona_parameters": "TEXT NOT NULL DEFAULT '{}'",
        "model_name": "VARCHAR(128)",
        "run_id": "VARCHAR(64)",
    }
    with engine.begin() as connection:
        for column_name, definition in additions.items():
            if column_name not in session_columns:
                connection.execute(text(f"ALTER TABLE sessions ADD COLUMN {column_name} {definition}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
