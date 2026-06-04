from sqlalchemy import Boolean, Column, Integer, JSON, String, Table, Text

from models.base import metadata

powerbi_connections = Table(
    "powerbi_connections",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("label", String, nullable=False),
    Column("tenant_id", String, nullable=False),
    Column("authority_base", String, nullable=False),
    Column("client_id", String),
    Column("redirect_uri", String, nullable=False),
    Column("scopes", Text, nullable=False),
    Column("owner_tenant_id", String),
    Column("owner_user_id", String),
    Column("owner_user_name", String),
    Column("owner_user_email", String),
    Column("active_workspace_id", String),
    Column("active_workspace_name", String),
    Column("active_semantic_model_id", String),
    Column("active_semantic_model_name", String),
    Column("is_active", Boolean, nullable=False, default=False),
    Column("last_authenticated_at", String),
    Column("last_selected_at", String),
    Column("raw", JSON),
)

powerbi_sessions = Table(
    "powerbi_sessions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("connection_id", Integer),
    Column("state", String, nullable=False, unique=True),
    Column("code_verifier", String, nullable=False),
    Column("access_token", Text),
    Column("refresh_token", Text),
    Column("expires_at", String),
    Column("tenant_id", String),
    Column("user_id", String),
    Column("user_name", String),
    Column("user_email", String),
    Column("raw", JSON),
)

powerbi_workspaces = Table(
    "powerbi_workspaces",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("connection_id", Integer),
    Column("session_id", Integer, nullable=False),
    Column("workspace_id", String, nullable=False),
    Column("workspace_name", String, nullable=False),
    Column("raw", JSON),
    Column("last_synced_at", String),
)

powerbi_semantic_models = Table(
    "powerbi_semantic_models",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("connection_id", Integer),
    Column("session_id", Integer, nullable=False),
    Column("workspace_id", String, nullable=False),
    Column("workspace_name", String, nullable=False),
    Column("semantic_model_id", String, nullable=False),
    Column("semantic_model_name", String, nullable=False),
    Column("source_reference", JSON),
    Column("raw", JSON),
    Column("selected_at", String),
)

project_semantic_model_cache = Table(
    "project_semantic_model_cache",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("project_id", Integer, nullable=False),
    Column("semantic_model_row_id", Integer, nullable=False),
    Column("cache_version", Integer, nullable=False),
    Column("raw", JSON),
    Column("field_catalog", JSON),
    Column("table_catalog", JSON),
    Column("relationship_catalog", JSON),
    Column("refreshed_at", String),
)
