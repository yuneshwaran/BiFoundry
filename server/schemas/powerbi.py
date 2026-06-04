from pydantic import BaseModel, Field


class PowerBIConnectionCreate(BaseModel):
    label: str = "Power BI Connection"
    tenant_id: str | None = None
    authority_base: str | None = None
    client_id: str | None = None
    redirect_uri: str | None = None
    scopes: list[str] | str | None = None
    owner_tenant_id: str | None = None
    owner_user_id: str | None = None
    owner_user_name: str | None = None
    owner_user_email: str | None = None
    active_workspace_id: str | None = None
    active_workspace_name: str | None = None
    active_semantic_model_id: str | None = None
    active_semantic_model_name: str | None = None
    is_active: bool | None = None
    raw: dict | None = None


class PowerBIConnectionUpdate(BaseModel):
    label: str | None = None
    tenant_id: str | None = None
    authority_base: str | None = None
    client_id: str | None = None
    redirect_uri: str | None = None
    scopes: list[str] | str | None = None
    owner_tenant_id: str | None = None
    owner_user_id: str | None = None
    owner_user_name: str | None = None
    owner_user_email: str | None = None
    active_workspace_id: str | None = None
    active_workspace_name: str | None = None
    active_semantic_model_id: str | None = None
    active_semantic_model_name: str | None = None
    is_active: bool | None = None
    raw: dict | None = None


class PowerBISessionOut(BaseModel):
    id: int
    connection_id: int | None = None
    state: str
    tenant_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    expires_at: str | None = None
    is_authenticated: bool
    raw: dict = Field(default_factory=dict)


class PowerBIConnectionOut(BaseModel):
    id: int
    label: str
    tenant_id: str | None = None
    authority_base: str | None = None
    client_id: str | None = None
    redirect_uri: str | None = None
    scopes: str | None = None
    owner_tenant_id: str | None = None
    owner_user_id: str | None = None
    owner_user_name: str | None = None
    owner_user_email: str | None = None
    active_workspace_id: str | None = None
    active_workspace_name: str | None = None
    active_semantic_model_id: str | None = None
    active_semantic_model_name: str | None = None
    is_active: bool
    last_authenticated_at: str | None = None
    last_selected_at: str | None = None
    raw: dict = Field(default_factory=dict)
    session: PowerBISessionOut | None = None


class PowerBIConnectionsList(BaseModel):
    connections: list[PowerBIConnectionOut]
    active_connection_id: int | None = None
    defaults: dict


class PowerBISessionWithConnectionOut(BaseModel):
    session: PowerBISessionOut
    connection: PowerBIConnectionOut


class PowerBILoginStartResponse(BaseModel):
    session_id: int
    connection_id: int
    state: str
    authorization_url: str
    redirect_uri: str


class PowerBIWorkspaceOut(BaseModel):
    id: int
    connection_id: int
    workspace_id: str
    name: str
    raw: dict


class PowerBISemanticModelOut(BaseModel):
    id: int
    connection_id: int
    workspace_id: str
    workspace_name: str
    semantic_model_id: str
    semantic_model_name: str
    raw: dict


class PowerBISemanticModelSelectPayload(BaseModel):
    workspace_id: str
    semantic_model_id: str


class PowerBISelectedSemanticModelOut(BaseModel):
    connection_id: int
    semantic_model_row_id: int
    workspace_id: str
    workspace_name: str
    semantic_model_id: str
    semantic_model_name: str
    source_reference: dict = Field(default_factory=dict)
    raw: dict = Field(default_factory=dict)
