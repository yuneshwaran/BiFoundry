from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import delete, select, update

from config import (
    POWER_BI_AUTHORITY_BASE,
    POWER_BI_CLIENT_ID,
    POWER_BI_REDIRECT_URI,
    POWER_BI_SCOPES,
    POWER_BI_TENANT_ID,
)
from database import engine, init_db
from models import (
    powerbi_connections,
    powerbi_sessions,
    powerbi_workspaces,
    powerbi_semantic_models,
    project_semantic_model_cache,
)
from services.powerbi_client import PowerBIClient, decode_jwt_claims, generate_pkce_pair, iso_now
from services.utils import _as_dict, _now, _read_one, _read_many


def _normalize_scopes(scopes):
    if isinstance(scopes, str):
        return scopes.strip()
    if isinstance(scopes, (list, tuple)):
        return " ".join(str(scope).strip() for scope in scopes if str(scope).strip())
    return None


def _connection_defaults():
    return {
        "tenant_id": POWER_BI_TENANT_ID,
        "authority_base": POWER_BI_AUTHORITY_BASE,
        "client_id": POWER_BI_CLIENT_ID,
        "redirect_uri": POWER_BI_REDIRECT_URI,
        "scopes": POWER_BI_SCOPES,
    }


def _strip_or_none(value):
    if value is None:
        return None
    return str(value).strip()


def _resolved_connection_value(connection_row, field_name, default_value=None):
    if connection_row and field_name in connection_row:
        value = connection_row.get(field_name)
        if value is not None:
            return value
    return default_value


def _connection_payload_from_row(connection_row):
    payload = {
        "tenant_id": _resolved_connection_value(connection_row, "tenant_id", POWER_BI_TENANT_ID),
        "authority_base": _resolved_connection_value(connection_row, "authority_base", POWER_BI_AUTHORITY_BASE),
        "client_id": _resolved_connection_value(connection_row, "client_id", POWER_BI_CLIENT_ID),
        "redirect_uri": _resolved_connection_value(connection_row, "redirect_uri", POWER_BI_REDIRECT_URI),
        "scopes": _resolved_connection_value(connection_row, "scopes", POWER_BI_SCOPES),
    }
    if not payload["tenant_id"] or str(payload["tenant_id"]).strip().lower() == "common":
        raise HTTPException(
            status_code=400,
            detail="A tenant-specific Power BI profile is required. Configure a tenant id in Settings.",
        )
    return payload


def _load_connection_by_id(conn, connection_id):
    return _read_one(conn, select(powerbi_connections).where(powerbi_connections.c.id == connection_id))


def _load_latest_session_for_connection(conn, connection_id):
    rows = _read_many(
        conn,
        select(powerbi_sessions)
        .where(powerbi_sessions.c.connection_id == connection_id)
        .order_by(powerbi_sessions.c.id.desc()),
    )
    if not rows:
        return None
    authenticated = [row for row in rows if row.get("access_token")]
    return authenticated[0] if authenticated else rows[0]


def _load_session_by_id(conn, session_id):
    return _read_one(conn, select(powerbi_sessions).where(powerbi_sessions.c.id == session_id))


def _load_session_by_state(conn, state):
    return _read_one(conn, select(powerbi_sessions).where(powerbi_sessions.c.state == state))


def _load_connection_from_session(conn, session_row):
    if not session_row:
        return None
    connection_id = session_row.get("connection_id")
    if connection_id:
        return _load_connection_by_id(conn, connection_id)
    return None


def _connection_client(connection_row, access_token=None):
    if not connection_row:
        raise HTTPException(status_code=404, detail="Power BI connection was not found.")
    connection_payload = _connection_payload_from_row(connection_row)
    return PowerBIClient(
        access_token=access_token,
        authority_base=connection_payload["authority_base"],
        tenant_id=connection_payload["tenant_id"],
        client_id=connection_payload["client_id"],
        redirect_uri=connection_payload["redirect_uri"],
        scopes=connection_payload["scopes"],
    )


def _session_client(conn, session_row):
    if not session_row or not session_row.get("access_token"):
        raise HTTPException(status_code=401, detail="Power BI session is not authenticated.")
    connection_row = _load_connection_from_session(conn, session_row)
    if connection_row:
        return _connection_client(connection_row, session_row["access_token"])
    return PowerBIClient(session_row["access_token"])


def _upsert_workspace(conn, connection_id, session_id, workspace):
    criteria = [
        powerbi_workspaces.c.session_id == session_id,
        powerbi_workspaces.c.workspace_id == workspace.get("id"),
    ]
    if connection_id is not None:
        criteria = [
            powerbi_workspaces.c.connection_id == connection_id,
            powerbi_workspaces.c.workspace_id == workspace.get("id"),
        ]
    existing = _read_one(
        conn,
        select(powerbi_workspaces).where(*criteria),
    )
    payload = {
        "connection_id": connection_id,
        "session_id": session_id,
        "workspace_id": workspace.get("id"),
        "workspace_name": workspace.get("name") or workspace.get("displayName") or workspace.get("id"),
        "raw": workspace,
        "last_synced_at": _now(),
    }
    if existing:
        conn.execute(update(powerbi_workspaces).where(powerbi_workspaces.c.id == existing["id"]).values(**payload))
        return existing["id"]
    result = conn.execute(powerbi_workspaces.insert().values(**payload))
    return result.inserted_primary_key[0]


def _upsert_semantic_model(conn, connection_id, session_id, workspace_id, workspace_name, semantic_model):
    criteria = [
        powerbi_semantic_models.c.session_id == session_id,
        powerbi_semantic_models.c.workspace_id == workspace_id,
        powerbi_semantic_models.c.semantic_model_id == semantic_model.get("id"),
    ]
    if connection_id is not None:
        criteria = [
            powerbi_semantic_models.c.connection_id == connection_id,
            powerbi_semantic_models.c.workspace_id == workspace_id,
            powerbi_semantic_models.c.semantic_model_id == semantic_model.get("id"),
        ]
    existing = _read_one(
        conn,
        select(powerbi_semantic_models).where(*criteria),
    )
    payload = {
        "connection_id": connection_id,
        "session_id": session_id,
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "semantic_model_id": semantic_model.get("id"),
        "semantic_model_name": semantic_model.get("name") or semantic_model.get("datasetName") or semantic_model.get("id"),
        "source_reference": {
            "provider": "powerbi",
            "workspaceId": workspace_id,
            "workspaceName": workspace_name,
            "semanticModelId": semantic_model.get("id"),
            "semanticModelName": semantic_model.get("name") or semantic_model.get("datasetName") or semantic_model.get("id"),
        },
        "raw": semantic_model,
        "selected_at": _now(),
    }
    if existing:
        conn.execute(update(powerbi_semantic_models).where(powerbi_semantic_models.c.id == existing["id"]).values(**payload))
        return existing["id"]
    result = conn.execute(powerbi_semantic_models.insert().values(**payload))
    return result.inserted_primary_key[0]


def _serialize_session(session_row):
    if not session_row:
        return None
    return {
        "id": session_row["id"],
        "connection_id": session_row.get("connection_id"),
        "state": session_row["state"],
        "tenant_id": session_row.get("tenant_id"),
        "user_id": session_row.get("user_id"),
        "user_name": session_row.get("user_name"),
        "user_email": session_row.get("user_email"),
        "expires_at": session_row.get("expires_at"),
        "is_authenticated": bool(session_row.get("access_token")),
        "raw": session_row.get("raw") or {},
    }


def _serialize_connection(conn, connection_row):
    latest_session = _load_latest_session_for_connection(conn, connection_row["id"])
    return {
        "id": connection_row["id"],
        "label": connection_row["label"],
        "tenant_id": connection_row.get("tenant_id"),
        "authority_base": connection_row.get("authority_base"),
        "client_id": connection_row.get("client_id"),
        "redirect_uri": connection_row.get("redirect_uri"),
        "scopes": connection_row.get("scopes"),
        "owner_tenant_id": connection_row.get("owner_tenant_id"),
        "owner_user_id": connection_row.get("owner_user_id"),
        "owner_user_name": connection_row.get("owner_user_name"),
        "owner_user_email": connection_row.get("owner_user_email"),
        "active_workspace_id": connection_row.get("active_workspace_id"),
        "active_workspace_name": connection_row.get("active_workspace_name"),
        "active_semantic_model_id": connection_row.get("active_semantic_model_id"),
        "active_semantic_model_name": connection_row.get("active_semantic_model_name"),
        "is_active": bool(connection_row.get("is_active")),
        "last_authenticated_at": connection_row.get("last_authenticated_at"),
        "last_selected_at": connection_row.get("last_selected_at"),
        "raw": connection_row.get("raw") or {},
        "session": _serialize_session(latest_session),
    }


def _activate_connection(conn, connection_id):
    conn.execute(update(powerbi_connections).values(is_active=False))
    conn.execute(update(powerbi_connections).where(powerbi_connections.c.id == connection_id).values(is_active=True))


def _connection_row_or_404(conn, connection_id):
    connection_row = _load_connection_by_id(conn, connection_id)
    if not connection_row:
        raise HTTPException(status_code=404, detail="Power BI connection was not found.")
    return connection_row


def list_powerbi_connections():
    init_db()
    with engine.begin() as conn:
        rows = _read_many(
            conn,
            select(powerbi_connections).order_by(powerbi_connections.c.is_active.desc(), powerbi_connections.c.id.desc()),
        )
        active_connection_id = None
        results = []
        for row in rows:
            if row.get("is_active") and active_connection_id is None:
                active_connection_id = row["id"]
            results.append(_serialize_connection(conn, row))
        if active_connection_id is None and results:
            active_connection_id = results[0]["id"]
    return {
        "connections": results,
        "active_connection_id": active_connection_id,
        "defaults": _connection_defaults(),
    }


def get_powerbi_connection(connection_id):
    init_db()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        return _serialize_connection(conn, connection_row)


def create_powerbi_connection(payload):
    init_db()
    payload = _as_dict(payload)
    label = (payload.get("label") or "Power BI Connection").strip()
    tenant_id = _strip_or_none(payload.get("tenant_id"))
    authority_base = _strip_or_none(payload.get("authority_base"))
    client_id = _strip_or_none(payload.get("client_id"))
    redirect_uri = _strip_or_none(payload.get("redirect_uri"))
    scopes = _normalize_scopes(payload.get("scopes"))
    raw = payload.get("raw") or {}
    with engine.begin() as conn:
        has_active = _read_one(conn, select(powerbi_connections.c.id).where(powerbi_connections.c.is_active.is_(True)))
        values = {
            "label": label,
            "tenant_id": tenant_id,
            "authority_base": authority_base,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "owner_tenant_id": payload.get("owner_tenant_id"),
            "owner_user_id": payload.get("owner_user_id"),
            "owner_user_name": payload.get("owner_user_name"),
            "owner_user_email": payload.get("owner_user_email"),
            "active_workspace_id": payload.get("active_workspace_id"),
            "active_workspace_name": payload.get("active_workspace_name"),
            "active_semantic_model_id": payload.get("active_semantic_model_id"),
            "active_semantic_model_name": payload.get("active_semantic_model_name"),
            "is_active": bool(payload.get("is_active")) or not has_active,
            "raw": raw,
        }
        result = conn.execute(powerbi_connections.insert().values(**values))
        connection_id = result.inserted_primary_key[0]
        if values["is_active"]:
            _activate_connection(conn, connection_id)
        connection_row = _load_connection_by_id(conn, connection_id)
        return _serialize_connection(conn, connection_row)


def update_powerbi_connection(connection_id, payload):
    init_db()
    payload = _as_dict(payload)
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        values = {}
        for key in ("label", "owner_tenant_id", "owner_user_id", "owner_user_name", "owner_user_email", "active_workspace_id", "active_workspace_name", "active_semantic_model_id", "active_semantic_model_name"):
            if key in payload and payload[key] is not None:
                values[key] = payload[key]
        for key in ("tenant_id", "authority_base", "client_id", "redirect_uri"):
            if key in payload:
                values[key] = _strip_or_none(payload.get(key))
        if "scopes" in payload:
            values["scopes"] = _normalize_scopes(payload.get("scopes"))
        if "raw" in payload and payload["raw"] is not None:
            values["raw"] = payload["raw"]
        if values:
            conn.execute(update(powerbi_connections).where(powerbi_connections.c.id == connection_id).values(**values))
        connection_row = _load_connection_by_id(conn, connection_id)
        return _serialize_connection(conn, connection_row)


def select_powerbi_connection(connection_id):
    init_db()
    with engine.begin() as conn:
        _connection_row_or_404(conn, connection_id)
        _activate_connection(conn, connection_id)
    return get_powerbi_connection(connection_id)


def delete_powerbi_connection(connection_id):
    init_db()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        session_ids = [row["id"] for row in _read_many(conn, select(powerbi_sessions.c.id).where(powerbi_sessions.c.connection_id == connection_id))]
        workspace_ids = [row["id"] for row in _read_many(conn, select(powerbi_workspaces.c.id).where(powerbi_workspaces.c.connection_id == connection_id))]
        semantic_model_ids = [row["id"] for row in _read_many(conn, select(powerbi_semantic_models.c.id).where(powerbi_semantic_models.c.connection_id == connection_id))]
        if semantic_model_ids:
            conn.execute(delete(project_semantic_model_cache).where(project_semantic_model_cache.c.semantic_model_row_id.in_(semantic_model_ids)))
        if workspace_ids:
            conn.execute(delete(powerbi_semantic_models).where(powerbi_semantic_models.c.connection_id == connection_id))
            conn.execute(delete(powerbi_workspaces).where(powerbi_workspaces.c.connection_id == connection_id))
        if session_ids:
            conn.execute(delete(powerbi_sessions).where(powerbi_sessions.c.connection_id == connection_id))
        conn.execute(delete(powerbi_connections).where(powerbi_connections.c.id == connection_id))
        remaining = _read_one(conn, select(powerbi_connections.c.id).order_by(powerbi_connections.c.id.asc()).limit(1))
        if remaining:
            conn.execute(update(powerbi_connections).where(powerbi_connections.c.id == remaining["id"]).values(is_active=True))
    return {"message": "Power BI connection deleted successfully.", "id": connection_id, "label": connection_row["label"]}


def start_powerbi_login(connection_id):
    init_db()
    state, verifier = generate_pkce_pair()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        client = _connection_client(connection_row)
        login = client.build_login_request(state, verifier)
        result = conn.execute(
            powerbi_sessions.insert().values(
                connection_id=connection_id,
                state=state,
                code_verifier=verifier,
                raw={"login": login, "created_at": _now()},
            )
        )
        session_id = result.inserted_primary_key[0]
    return {
        "session_id": session_id,
        "connection_id": connection_id,
        "state": state,
        "authorization_url": login["authorization_url"],
        "redirect_uri": login["redirect_uri"],
    }


def complete_powerbi_login(state, code):
    init_db()
    if not state or not code:
        raise HTTPException(status_code=400, detail="Both 'state' and 'code' are required.")
    with engine.begin() as conn:
        session_row = _load_session_by_state(conn, state)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI login session was not found.")
        connection_row = _connection_row_or_404(conn, session_row["connection_id"])
        client = _connection_client(connection_row)
        token_payload = client.exchange_code(code, session_row["code_verifier"])
        claims = decode_jwt_claims(token_payload.get("id_token"))
        expires_in = token_payload.get("expires_in") or 3600
        expires_at = datetime.now(timezone.utc).timestamp() + int(expires_in)
        session_update = {
            "access_token": token_payload.get("access_token"),
            "refresh_token": token_payload.get("refresh_token"),
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "tenant_id": claims.get("tid"),
            "user_id": claims.get("oid") or claims.get("sub"),
            "user_name": claims.get("name") or claims.get("preferred_username"),
            "user_email": claims.get("preferred_username") or claims.get("upn") or claims.get("email"),
            "raw": {"token": token_payload, "claims": claims},
        }
        conn.execute(update(powerbi_sessions).where(powerbi_sessions.c.id == session_row["id"]).values(**session_update))
        conn.execute(
            update(powerbi_connections)
            .where(powerbi_connections.c.id == connection_row["id"])
            .values(
                owner_tenant_id=claims.get("tid"),
                owner_user_id=claims.get("oid") or claims.get("sub"),
                owner_user_name=claims.get("name") or claims.get("preferred_username"),
                owner_user_email=claims.get("preferred_username") or claims.get("upn") or claims.get("email"),
                last_authenticated_at=iso_now(),
                is_active=True,
            )
        )
        _activate_connection(conn, connection_row["id"])
        updated_session = _load_session_by_id(conn, session_row["id"])
        updated_connection = _load_connection_by_id(conn, connection_row["id"])
        return {
            "session": _serialize_session(updated_session),
            "connection": _serialize_connection(conn, updated_connection),
        }


def get_powerbi_session(session_id):
    init_db()
    with engine.begin() as conn:
        session_row = _load_session_by_id(conn, session_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI session was not found.")
        connection_row = _load_connection_by_id(conn, session_row.get("connection_id"))
        session = _serialize_session(session_row)
        session["connection"] = _serialize_connection(conn, connection_row) if connection_row else None
    return session


def refresh_powerbi_session(session_id):
    init_db()
    with engine.begin() as conn:
        session_row = _load_session_by_id(conn, session_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI session was not found.")
        if not session_row.get("refresh_token"):
            raise HTTPException(status_code=400, detail="The Power BI session does not have a refresh token.")
        connection_row = _load_connection_by_id(conn, session_row.get("connection_id"))
        client = _connection_client(connection_row)
        token_payload = client.refresh_token(session_row["refresh_token"])
        claims = decode_jwt_claims(token_payload.get("id_token"))
        expires_in = token_payload.get("expires_in") or 3600
        expires_at = datetime.now(timezone.utc).timestamp() + int(expires_in)
        values = {
            "access_token": token_payload.get("access_token"),
            "refresh_token": token_payload.get("refresh_token") or session_row.get("refresh_token"),
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "tenant_id": claims.get("tid") or session_row.get("tenant_id"),
            "user_id": claims.get("oid") or claims.get("sub") or session_row.get("user_id"),
            "user_name": claims.get("name") or claims.get("preferred_username") or session_row.get("user_name"),
            "user_email": claims.get("preferred_username") or claims.get("upn") or claims.get("email") or session_row.get("user_email"),
            "raw": {"token": token_payload, "claims": claims},
        }
        conn.execute(update(powerbi_sessions).where(powerbi_sessions.c.id == session_row["id"]).values(**values))
        conn.execute(
            update(powerbi_connections)
            .where(powerbi_connections.c.id == session_row.get("connection_id"))
            .values(
                owner_tenant_id=values["tenant_id"],
                owner_user_id=values["user_id"],
                owner_user_name=values["user_name"],
                owner_user_email=values["user_email"],
                last_authenticated_at=iso_now(),
            )
        )
        updated_session = _load_session_by_id(conn, session_row["id"])
    return _serialize_session(updated_session)


def refresh_powerbi_connection(connection_id):
    init_db()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        session_row = _load_latest_session_for_connection(conn, connection_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI connection does not have a session yet.")
        if not session_row.get("refresh_token"):
            raise HTTPException(status_code=400, detail="The Power BI session does not have a refresh token.")
        client = _connection_client(connection_row)
        token_payload = client.refresh_token(session_row["refresh_token"])
        claims = decode_jwt_claims(token_payload.get("id_token"))
        expires_in = token_payload.get("expires_in") or 3600
        expires_at = datetime.now(timezone.utc).timestamp() + int(expires_in)
        values = {
            "access_token": token_payload.get("access_token"),
            "refresh_token": token_payload.get("refresh_token") or session_row.get("refresh_token"),
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "tenant_id": claims.get("tid") or session_row.get("tenant_id"),
            "user_id": claims.get("oid") or claims.get("sub") or session_row.get("user_id"),
            "user_name": claims.get("name") or claims.get("preferred_username") or session_row.get("user_name"),
            "user_email": claims.get("preferred_username") or claims.get("upn") or claims.get("email") or session_row.get("user_email"),
            "raw": {"token": token_payload, "claims": claims},
        }
        conn.execute(update(powerbi_sessions).where(powerbi_sessions.c.id == session_row["id"]).values(**values))
        conn.execute(
            update(powerbi_connections)
            .where(powerbi_connections.c.id == connection_id)
            .values(
                owner_tenant_id=values["tenant_id"],
                owner_user_id=values["user_id"],
                owner_user_name=values["user_name"],
                owner_user_email=values["user_email"],
                last_authenticated_at=iso_now(),
            )
        )
        updated_session = _load_session_by_id(conn, session_row["id"])
    return _serialize_session(updated_session)


def delete_powerbi_session(session_id):
    init_db()
    with engine.begin() as conn:
        session_row = _load_session_by_id(conn, session_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI session was not found.")
        conn.execute(delete(powerbi_sessions).where(powerbi_sessions.c.id == session_id))
    return {"message": "Power BI session deleted successfully.", "id": session_id}


def list_powerbi_workspaces(connection_id):
    init_db()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        session_row = _load_latest_session_for_connection(conn, connection_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI connection does not have an authenticated session.")
        client = _session_client(conn, session_row)
        workspaces = client.list_workspaces()
        results = []
        for workspace in workspaces:
            workspace_id = _upsert_workspace(conn, connection_id, session_row["id"], workspace)
            results.append(
                {
                    "id": workspace_id,
                    "connection_id": connection_id,
                    "workspace_id": workspace.get("id"),
                    "name": workspace.get("name") or workspace.get("displayName") or workspace.get("id"),
                    "raw": workspace,
                }
            )
    return results


def list_powerbi_semantic_models(connection_id, workspace_id):
    init_db()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        session_row = _load_latest_session_for_connection(conn, connection_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI connection does not have an authenticated session.")
        client = _session_client(conn, session_row)
        workspace_row = _read_one(
            conn,
            select(powerbi_workspaces).where(
                powerbi_workspaces.c.connection_id == connection_id,
                powerbi_workspaces.c.workspace_id == workspace_id,
            ),
        )
        workspace_name = workspace_row["workspace_name"] if workspace_row else workspace_id
        models = client.list_semantic_models(workspace_id)
        results = []
        for semantic_model in models:
            row_id = _upsert_semantic_model(conn, connection_id, session_row["id"], workspace_id, workspace_name, semantic_model)
            results.append(
                {
                    "id": row_id,
                    "connection_id": connection_id,
                    "workspace_id": workspace_id,
                    "workspace_name": workspace_name,
                    "semantic_model_id": semantic_model.get("id"),
                    "semantic_model_name": semantic_model.get("name") or semantic_model.get("datasetName") or semantic_model.get("id"),
                    "raw": semantic_model,
                }
            )
    return results


def select_powerbi_semantic_model(connection_id, workspace_id, semantic_model_id):
    init_db()
    with engine.begin() as conn:
        connection_row = _connection_row_or_404(conn, connection_id)
        session_row = _load_latest_session_for_connection(conn, connection_id)
        if not session_row:
            raise HTTPException(status_code=404, detail="Power BI connection does not have an authenticated session.")
        client = _session_client(conn, session_row)
        workspace_row = _read_one(
            conn,
            select(powerbi_workspaces).where(
                powerbi_workspaces.c.connection_id == connection_id,
                powerbi_workspaces.c.workspace_id == workspace_id,
            ),
        )
        workspace_name = workspace_row["workspace_name"] if workspace_row else workspace_id
        semantic_model = client.get_semantic_model(workspace_id, semantic_model_id)
        try:
            tables = client.get_semantic_model_tables(workspace_id, semantic_model_id)
        except HTTPException:
            tables = []
        try:
            datasources = client.get_semantic_model_datasources(workspace_id, semantic_model_id)
        except HTTPException:
            datasources = []
        semantic_model_row_id = _upsert_semantic_model(conn, connection_id, session_row["id"], workspace_id, workspace_name, semantic_model)
        conn.execute(
            update(powerbi_semantic_models)
            .where(powerbi_semantic_models.c.id == semantic_model_row_id)
            .values(
                raw={
                    "workspace": workspace_row or {"workspace_id": workspace_id, "workspace_name": workspace_name},
                    "semantic_model": semantic_model,
                    "tables": tables,
                    "datasources": datasources,
                },
                source_reference={
                    "provider": "powerbi",
                    "workspaceId": workspace_id,
                    "workspaceName": workspace_name,
                    "semanticModelId": semantic_model_id,
                    "semanticModelName": semantic_model.get("name") or semantic_model.get("datasetName") or semantic_model_id,
                },
            )
        )
        conn.execute(
            update(powerbi_connections)
            .where(powerbi_connections.c.id == connection_id)
            .values(
                active_workspace_id=workspace_id,
                active_workspace_name=workspace_name,
                active_semantic_model_id=semantic_model_id,
                active_semantic_model_name=semantic_model.get("name") or semantic_model.get("datasetName") or semantic_model_id,
                last_selected_at=iso_now(),
                is_active=True,
            )
        )
        _activate_connection(conn, connection_id)
        selected = _read_one(
            conn,
            select(powerbi_semantic_models).where(powerbi_semantic_models.c.id == semantic_model_row_id),
        )
    return {
        "connection_id": connection_id,
        "semantic_model_row_id": selected["id"],
        "workspace_id": selected["workspace_id"],
        "workspace_name": selected["workspace_name"],
        "semantic_model_id": selected["semantic_model_id"],
        "semantic_model_name": selected["semantic_model_name"],
        "source_reference": selected.get("source_reference") or {},
        "raw": selected.get("raw") or {},
    }
