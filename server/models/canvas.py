from sqlalchemy import Column, Integer, JSON, String, Table, Text

from models.base import metadata

visual_templates = Table(
    "visual_templates",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("visual_type", String, nullable=False),
    Column("slot_definitions", JSON, nullable=False),
    Column("default_format", JSON),
    Column("is_active", String, default="1"),
    Column("template_key", String),
    Column("category", String),
    Column("icon", String),
    Column("description", Text),
    Column("default_width", Integer),
    Column("default_height", Integer),
    Column("required_slots", JSON),
    Column("optional_slots", JSON),
    Column("default_visual_json", JSON),
)

canvas_reports = Table(
    "canvas_reports",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("project_id", Integer),
    Column("settings", JSON),
    Column("created_at", String),
    Column("description", Text),
    Column("source_semantic_model_id", Integer),
    Column("source_semantic_model_name", String),
    Column("canvas_settings", JSON),
    Column("report_settings", JSON),
    Column("raw", JSON),
)

canvas_pages = Table(
    "canvas_pages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("canvas_report_id", Integer, nullable=False),
    Column("page_name", String),
    Column("display_name", String),
    Column("page_order", Integer, nullable=False),
    Column("name", String, nullable=False),
    Column("settings", JSON),
    Column("width", Integer),
    Column("height", Integer),
    Column("raw", JSON),
)

canvas_visuals = Table(
    "canvas_visuals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("canvas_page_id", Integer, nullable=False),
    Column("visual_template_id", Integer),
    Column("visual_name", String),
    Column("grid_position", JSON),
    Column("field_bindings", JSON),
    Column("format_config", JSON),
    Column("tab_order", Integer),
    Column("visual_order", Integer, nullable=False),
    Column("template_key", String, nullable=False),
    Column("name", String, nullable=False),
    Column("x", Integer),
    Column("y", Integer),
    Column("w", Integer),
    Column("h", Integer),
    Column("bindings", JSON),
    Column("config", JSON),
    Column("raw", JSON),
)

dataset_fields = Table(
    "dataset_fields",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("dataset_id", Integer, nullable=False),
    Column("table_name", String, nullable=False),
    Column("field_name", String, nullable=False),
    Column("field_type", String, nullable=False),
    Column("data_type", String),
    Column("dax_expression", Text),
)
