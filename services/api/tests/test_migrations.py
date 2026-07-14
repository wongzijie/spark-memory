from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from app.config import get_settings


def test_foundation_migration_round_trip():
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(get_settings().database_url)
    try:
        inspector = inspect(engine)
        expected_tables = {
            "users",
            "sessions",
            "raw_captures",
            "normalized_contents",
            "processing_jobs",
        }
        assert set(inspector.get_table_names()) >= expected_tables

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()).isdisjoint(expected_tables)

        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= expected_tables
        capture_constraints = {
            item["name"] for item in inspector.get_unique_constraints("raw_captures")
        }
        job_constraints = {
            item["name"] for item in inspector.get_unique_constraints("processing_jobs")
        }
        assert "uq_capture_telegram_update" in capture_constraints
        assert "uq_capture_job_kind" in job_constraints
        assert {item["name"] for item in inspector.get_enums()} >= {"job_kind", "job_state"}
    finally:
        engine.dispose()
