import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from config import (
    POWER_BI_AUTHORITY_BASE,
    POWER_BI_CLIENT_ID,
    POWER_BI_CLIENT_RETURN_URL,
    POWER_BI_REDIRECT_URI,
    POWER_BI_SCOPES,
    POWER_BI_TENANT_ID,
)
from schemas.powerbi import (
    PowerBIConnectionCreate,
    PowerBIConnectionUpdate,
    PowerBISemanticModelSelectPayload,
)
from services.powerbi_service import (
    complete_powerbi_login,
    create_powerbi_connection,
    delete_powerbi_connection,
    delete_powerbi_session,
    get_powerbi_connection,
    get_powerbi_session,
    list_powerbi_connections,
    list_powerbi_semantic_models,
    list_powerbi_workspaces,
    refresh_powerbi_connection,
    refresh_powerbi_session,
    select_powerbi_connection,
    select_powerbi_semantic_model,
    start_powerbi_login,
    update_powerbi_connection,
)

router = APIRouter(tags=["powerbi"])


def _resolve_connection_id(request: Request, connection_id: str | None = None):
    resolved = connection_id or request.headers.get("X-PowerBI-Connection") or request.headers.get("X-PowerBI-Session")
    if resolved is None:
        raise HTTPException(status_code=400, detail="Power BI connection id is required.")
    try:
        return int(resolved)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Power BI connection id must be an integer.")


async def _parse_semantic_model_select_payload(request: Request) -> PowerBISemanticModelSelectPayload:
    try:
        body = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Semantic model selection payload must be valid JSON.") from exc
    except Exception:
        body = None
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Semantic model selection payload must be a JSON object, not a JSON-encoded string.",
            ) from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Semantic model selection payload must be a JSON object.")
    try:
        return PowerBISemanticModelSelectPayload.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Both workspace_id and semantic_model_id are required.") from exc


@router.get("/powerbi/config")
def powerbi_config_route():
    return {
        "tenant_id": POWER_BI_TENANT_ID,
        "authority_base": POWER_BI_AUTHORITY_BASE,
        "client_id": POWER_BI_CLIENT_ID,
        "redirect_uri": POWER_BI_REDIRECT_URI,
        "scopes": POWER_BI_SCOPES,
    }


@router.get("/powerbi/connections")
def list_connections_route():
    return list_powerbi_connections()


@router.post("/powerbi/connections")
def create_connection_route(payload: PowerBIConnectionCreate):
    return create_powerbi_connection(payload)


@router.get("/powerbi/connections/{connection_id}")
def get_connection_route(connection_id: int):
    return get_powerbi_connection(connection_id)


@router.patch("/powerbi/connections/{connection_id}")
def update_connection_route(connection_id: int, payload: PowerBIConnectionUpdate):
    return update_powerbi_connection(connection_id, payload)


@router.delete("/powerbi/connections/{connection_id}")
def delete_connection_route(connection_id: int):
    return delete_powerbi_connection(connection_id)


@router.post("/powerbi/connections/{connection_id}/select")
def select_connection_route(connection_id: int):
    return select_powerbi_connection(connection_id)


@router.post("/powerbi/connections/{connection_id}/refresh")
def refresh_connection_route(connection_id: int):
    return refresh_powerbi_connection(connection_id)


@router.post("/powerbi/connections/{connection_id}/auth/login")
def start_login_route(connection_id: int, payload: dict | None = None):
    payload = payload or {}
    requested_connection_id = payload.get("connection_id")
    if requested_connection_id is not None and int(requested_connection_id) != connection_id:
        raise HTTPException(status_code=400, detail="Connection id in the body does not match the route.")
    return start_powerbi_login(connection_id)


@router.post("/powerbi/auth/login")
def start_login_compat_route(payload: dict | None = None):
    payload = payload or {}
    connection_id = payload.get("connection_id")
    if connection_id is None:
        raise HTTPException(status_code=400, detail="A connection_id is required to start Power BI login.")
    return start_powerbi_login(int(connection_id))


@router.get("/powerbi/auth/callback")
def callback_route(request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Power BI authentication failed: {error}. Description: {error_description}",
        )
    if not state or not code:
        # Include raw query parameters for debugging
        raw_params = dict(request.query_params)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required authentication parameters: 'state' and 'code' are required.",
                "received_params": raw_params,
            },
        )
    session = complete_powerbi_login(state, code)
    if POWER_BI_CLIENT_RETURN_URL:
        connection_id = session["connection"]["id"] if session.get("connection") else session["session"].get("connection_id")
        redirect_url = f"{POWER_BI_CLIENT_RETURN_URL}?powerbi_session={session['session']['id']}&powerbi_connection={connection_id}&state={session['session']['state']}"
        return RedirectResponse(url=redirect_url, status_code=302)
    return session



@router.get("/powerbi/auth/session/{session_id}")
def get_session_route(session_id: int):
    return get_powerbi_session(session_id)


@router.post("/powerbi/auth/session/{session_id}/refresh")
def refresh_session_route(session_id: int):
    return refresh_powerbi_session(session_id)


@router.post("/powerbi/connections/{connection_id}/session/refresh")
def refresh_connection_session_route(connection_id: int):
    return refresh_powerbi_connection(connection_id)


@router.delete("/powerbi/auth/session/{session_id}")
def delete_session_route(session_id: int):
    return delete_powerbi_session(session_id)


@router.get("/powerbi/workspaces")
def list_workspaces_route(request: Request, connection_id: str | None = None):
    return list_powerbi_workspaces(_resolve_connection_id(request, connection_id))


@router.get("/powerbi/connections/{connection_id}/workspaces")
def list_connection_workspaces_route(connection_id: int):
    return list_powerbi_workspaces(connection_id)


@router.get("/powerbi/workspaces/{workspace_id}/semantic-models")
def list_semantic_models_route(request: Request, workspace_id: str, connection_id: str | None = None):
    return list_powerbi_semantic_models(_resolve_connection_id(request, connection_id), workspace_id)


@router.get("/powerbi/connections/{connection_id}/workspaces/{workspace_id}/semantic-models")
def list_connection_semantic_models_route(connection_id: int, workspace_id: str):
    return list_powerbi_semantic_models(connection_id, workspace_id)


@router.post("/powerbi/semantic-models/select")
async def select_semantic_model_route(request: Request, connection_id: str | None = None):
    payload = await _parse_semantic_model_select_payload(request)
    resolved_connection_id = _resolve_connection_id(request, connection_id)
    return select_powerbi_semantic_model(
        resolved_connection_id,
        payload.workspace_id,
        payload.semantic_model_id,
    )


@router.post("/powerbi/connections/{connection_id}/semantic-models/select")
async def select_connection_semantic_model_route(connection_id: int, request: Request):
    payload = await _parse_semantic_model_select_payload(request)
    return select_powerbi_semantic_model(
        connection_id,
        payload.workspace_id,
        payload.semantic_model_id,
    )
