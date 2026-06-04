from sqlalchemy import Column, Integer, JSON, String, Text, Table

from models.base import metadata

semantic_models = Table(
    "semantic_models",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("original_filename", String),
    Column("semantic_format", String),
    Column("semantic_model_folder_name", String),
    Column("raw", JSON),
)

semantic_model_files = Table(
    "semantic_model_files",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("semantic_model_id", Integer, nullable=False),
    Column("relative_path", String, nullable=False),
    Column("artifact_scope", String, nullable=False),
    Column("content_kind", String, nullable=False),
    Column("text_content", Text),
    Column("json_content", JSON),
    Column("binary_base64", Text),
    Column("sha256", String),
    Column("size_bytes", Integer),
)
