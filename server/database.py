from sqlalchemy import create_engine, inspect, text

from config import DATABASE_URL
from models import (
    canvas_pages,
    canvas_reports,
    canvas_visuals,
    dataset_fields,
    metadata,
    powerbi_connections,
    powerbi_semantic_models,
    powerbi_sessions,
    powerbi_workspaces,
    visual_templates,
)

engine = create_engine(DATABASE_URL)


def _ensure_column(engine, table_name, column):
    with engine.begin() as conn:
        inspector = inspect(conn)
        existing = {item["name"] for item in inspector.get_columns(table_name)}
        if column.name in existing:
            return
        ddl = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {column.type.compile(dialect=engine.dialect)}'
        conn.execute(text(ddl))


def _ensure_canvas_schema():
    for table in (visual_templates, canvas_reports, canvas_pages, canvas_visuals):
        for column in table.columns:
            if column.primary_key:
                continue
            _ensure_column(engine, table.name, column)


def _ensure_powerbi_schema():
    for table in (powerbi_connections, powerbi_sessions, powerbi_workspaces, powerbi_semantic_models):
        for column in table.columns:
            if column.primary_key:
                continue
            _ensure_column(engine, table.name, column)


def init_db():
    metadata.create_all(engine)
    _ensure_canvas_schema()
    _ensure_powerbi_schema()
