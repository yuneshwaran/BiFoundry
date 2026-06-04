import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import HTTPException

from config import (
    POWER_BI_API_BASE,
    POWER_BI_AUTHORITY_BASE,
    POWER_BI_CLIENT_ID,
    POWER_BI_REDIRECT_URI,
    POWER_BI_SCOPES,
    POWER_BI_TENANT_ID,
    POWER_BI_CLIENT_SECRET,
)


class PowerBIClient:
    def __init__(
        self,
        access_token: str | None = None,
        authority_base: str | None = None,
        tenant_id: str | None = None,
        client_id: str | None = None,
        redirect_uri: str | None = None,
        scopes: str | None = None,
    ):
        self.access_token = access_token
        self.authority_base = POWER_BI_AUTHORITY_BASE if authority_base is None else authority_base
        self.tenant_id = "" if tenant_id is None else tenant_id
        self.client_id = POWER_BI_CLIENT_ID if client_id is None else client_id
        self.redirect_uri = POWER_BI_REDIRECT_URI if redirect_uri is None else redirect_uri
        self.scopes = POWER_BI_SCOPES if scopes is None else scopes

    @property
    def tenant_authority(self) -> str:
        return f"{self.authority_base.rstrip('/')}/{self.tenant_id}"

    @property
    def authorize_url(self) -> str:
        return f"{self.tenant_authority}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        return f"{self.tenant_authority}/oauth2/v2.0/token"

    def build_login_request(self, state: str, code_verifier: str) -> dict:
        if not self.authority_base:
            raise HTTPException(
                status_code=400,
                detail="An authority base is required for Power BI login.",
            )
        if not self.client_id:
            raise HTTPException(
                status_code=400,
                detail="A client id is required for Power BI login.",
            )
        if not self.tenant_id:
            raise HTTPException(
                status_code=400,
                detail="A tenant id is required for Power BI login.",
            )
        if not self.redirect_uri:
            raise HTTPException(
                status_code=400,
                detail="A redirect URI is required for Power BI login.",
            )
        if not self.scopes:
            raise HTTPException(
                status_code=400,
                detail="Power BI scopes are required for login.",
            )

        query = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": self.scopes,
            "state": state,
            "code_challenge": self._code_challenge(code_verifier),
            "code_challenge_method": "S256",
        }
        return {
            "authorization_url": f"{self.authorize_url}?{urllib.parse.urlencode(query)}",
            "redirect_uri": self.redirect_uri,
        }

    def exchange_code(self, code: str, code_verifier: str) -> dict:
        if not self.client_id:
            raise HTTPException(status_code=400, detail="A client id is required for token exchange.")
        body = {
            "client_id": self.client_id,
            "client_secret": POWER_BI_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "code_verifier": code_verifier,
        }
        return self._post_form(self.token_url, body)

    def refresh_token(self, refresh_token: str) -> dict:
        body = {
            "client_id": self.client_id,
            "client_secret": POWER_BI_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
        }
        return self._post_form(self.token_url, body)

    def get_current_user(self) -> dict:
        return self._get_json("https://graph.microsoft.com/v1.0/me")

    def list_workspaces(self) -> list[dict]:
        payload = self._get_json(f"{POWER_BI_API_BASE}/groups")
        return payload.get("value", []) if isinstance(payload, dict) else []

    def list_semantic_models(self, workspace_id: str) -> list[dict]:
        payload = self._get_json(f"{POWER_BI_API_BASE}/groups/{workspace_id}/datasets")
        return payload.get("value", []) if isinstance(payload, dict) else []

    def get_semantic_model(self, workspace_id: str, model_id: str) -> dict:
        return self._get_json(f"{POWER_BI_API_BASE}/groups/{workspace_id}/datasets/{model_id}")

    def get_semantic_model_datasources(self, workspace_id: str, model_id: str) -> list[dict]:
        payload = self._get_json(f"{POWER_BI_API_BASE}/groups/{workspace_id}/datasets/{model_id}/datasources")
        if not isinstance(payload, dict):
            return []
        return payload.get("value") or payload.get("datasources") or []

    def get_semantic_model_tables(self, workspace_id: str, model_id: str) -> list[dict]:
        payload = self._get_json(f"{POWER_BI_API_BASE}/groups/{workspace_id}/datasets/{model_id}/tables")
        if not isinstance(payload, dict):
            return []
        return payload.get("value") or payload.get("tables") or []

    def post_workspace_info_scan(
        self,
        workspace_ids: list[str],
        *,
        lineage: bool = True,
        datasource_details: bool = True,
        dataset_schema: bool = True,
        dataset_expressions: bool = True,
        get_artifact_users: bool = False,
    ) -> dict:
        params = {
            "lineage": str(bool(lineage)).lower(),
            "datasourceDetails": str(bool(datasource_details)).lower(),
            "datasetSchema": str(bool(dataset_schema)).lower(),
            "datasetExpressions": str(bool(dataset_expressions)).lower(),
            "getArtifactUsers": str(bool(get_artifact_users)).lower(),
        }
        payload = self._post_json(
            f"{POWER_BI_API_BASE}/admin/workspaces/getInfo?{urllib.parse.urlencode(params)}",
            {"workspaces": workspace_ids},
        )
        return payload if isinstance(payload, dict) else {}

    def get_workspace_scan_status(self, scan_id: str) -> dict:
        payload = self._get_json(f"{POWER_BI_API_BASE}/admin/workspaces/scanStatus/{scan_id}")
        return payload if isinstance(payload, dict) else {}

    def get_workspace_scan_result(self, scan_id: str) -> dict:
        payload = self._get_json(f"{POWER_BI_API_BASE}/admin/workspaces/scanResult/{scan_id}")
        return payload if isinstance(payload, dict) else {}

    def execute_semantic_model_query(self, workspace_id: str, model_id: str, dax_query: str) -> list[dict]:
        payload = self._post_json(
            f"{POWER_BI_API_BASE}/groups/{workspace_id}/datasets/{model_id}/executeQueries",
            {
                "queries": [{"query": dax_query}],
                "serializerSettings": {"includeNulls": True},
            },
        )
        if not isinstance(payload, dict):
            return []
        results = payload.get("results") or []
        if not results:
            return []
        result_tables = (results[0] or {}).get("tables") or []
        if not result_tables:
            return []
        return (result_tables[0] or {}).get("rows") or []

    def _post_form(self, url: str, data: dict) -> dict:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=encoded,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        return self._execute_json(request)

    def _post_json(self, url: str, data: dict) -> dict:
        encoded = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=encoded,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        return self._execute_json(request)

    def _get_json(self, url: str) -> dict:
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
        )
        return self._execute_json(request)

    def _execute_json(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {"error": body}
            raise HTTPException(status_code=exc.code, detail=payload.get("error_description") or payload.get("error") or payload)
        except urllib.error.URLError as exc:
            raise HTTPException(status_code=503, detail=f"Power BI request failed: {exc.reason}")

    def _code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(32)
    return state, verifier


def decode_jwt_claims(token: str | None) -> dict:
    if not token or token.count(".") < 2:
        return {}
    try:
        payload = token.split(".", 2)[1]
        padded = payload + "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
