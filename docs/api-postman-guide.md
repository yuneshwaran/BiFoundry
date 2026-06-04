# BiFoundry API Guide for Postman

This guide documents the current API surface and the simplest POC-friendly restructuring path.

## Simple POC Recommendation

Keep only two public API groups:

- `/api/powerbi/*` for connection, auth, workspace, and semantic model selection.
- `/api/projects/*` for project, page, visual, validation, and compile flow.

Treat the older `canvas_service.py` implementation as internal/legacy logic, not as a separate public API surface. For a simple POC, avoid multiplying route variants and keep one canonical route per action.

## Current Modules

- `server/api/powerbi.py`
- `server/api/project.py`
- `server/services/powerbi_service.py`
- `server/services/project_service.py`
- `server/schemas/powerbi.py`
- `server/schemas/canvas.py`
- `server/pbip_generator/report_writer.py`
- `server/pbip_generator/model_writer.py`

## Base URL

- Local default: `http://localhost:8000/api`

## Power BI APIs

### 1. Get config

- `GET /powerbi/config`
- No request body

Response example:

```json
{
  "tenant_id": "your-tenant-id",
  "authority_base": "https://login.microsoftonline.com",
  "client_id": "app-client-id",
  "redirect_uri": "http://localhost:8000/api/powerbi/auth/callback",
  "scopes": ["Dataset.Read.All", "Workspace.Read.All"]
}
```

### 2. Connections

#### List

- `GET /powerbi/connections`
- No request body

#### Create

- `POST /powerbi/connections`

Request body:

```json
{
  "label": "My Power BI Connection",
  "tenant_id": "tenant-id",
  "authority_base": "https://login.microsoftonline.com",
  "client_id": "client-id",
  "redirect_uri": "http://localhost:8000/api/powerbi/auth/callback",
  "scopes": ["Dataset.Read.All", "Workspace.Read.All"],
  "owner_tenant_id": "tenant-id",
  "owner_user_id": "user-id",
  "owner_user_name": "User Name",
  "owner_user_email": "user@example.com",
  "active_workspace_id": "workspace-id",
  "active_workspace_name": "Workspace Name",
  "active_semantic_model_id": "semantic-model-id",
  "active_semantic_model_name": "Semantic Model Name",
  "is_active": true,
  "raw": {}
}
```

#### Update

- `PATCH /powerbi/connections/{connection_id}`

Request body: same shape as create, but every field is optional.

#### Delete

- `DELETE /powerbi/connections/{connection_id}`
- No request body

### 3. Select / Refresh Connection

- `POST /powerbi/connections/{connection_id}/select`
- `POST /powerbi/connections/{connection_id}/refresh`

No request body.

### 4. Login

- `POST /powerbi/connections/{connection_id}/auth/login`
- Optional request body:

```json
{
  "connection_id": 1
}
```

Notes:
- The body `connection_id` must match the route id if sent.
- Compatibility route also exists:
  - `POST /powerbi/auth/login`
  - body:

```json
{
  "connection_id": 1
}
```

### 5. Callback

- `GET /powerbi/auth/callback?state=...&code=...`
- No JSON body

### 6. Sessions

- `GET /powerbi/auth/session/{session_id}`
- `POST /powerbi/auth/session/{session_id}/refresh`
- `DELETE /powerbi/auth/session/{session_id}`

No request body.

### 7. Workspaces

Canonical route:

- `GET /powerbi/workspaces`

How to send it:

- Either send header `X-PowerBI-Connection: <connection_id>`
- Or use query `?connection_id=<connection_id>`

Alternative route:

- `GET /powerbi/connections/{connection_id}/workspaces`

No request body.

### 8. Semantic Models

Canonical route:

- `GET /powerbi/workspaces/{workspace_id}/semantic-models`

How to send it:

- Header `X-PowerBI-Connection: <connection_id>`
- Or query `?connection_id=<connection_id>`

Alternative route:

- `GET /powerbi/connections/{connection_id}/workspaces/{workspace_id}/semantic-models`

#### Select semantic model

- `POST /powerbi/semantic-models/select`

Request body:

```json
{
  "workspace_id": "workspace-id",
  "semantic_model_id": "semantic-model-id"
}
```

Alternative route:

- `POST /powerbi/connections/{connection_id}/semantic-models/select`

Request body is the same.

## Project APIs

These are the main POC endpoints for creating and compiling a canvas project.

### 1. List projects

- `GET /projects`
- No request body

### 2. Create project

- `POST /projects`

Request body:

```json
{
  "name": "Sales",
  "description": "Optional description",
  "source_semantic_model_id": 123,
  "source_semantic_model_name": "Sales",
  "canvas_settings": {
    "width": 1280,
    "height": 720
  },
  "report_settings": {
    "themeName": "BIFoundryTheme",
    "themeColor": "#154360"
  },
  "raw": {
    "connection_id": 1,
    "session_id": 10,
    "workspace_id": "workspace-id",
    "semantic_model_id": "semantic-model-id",
    "semantic_model_row_id": "123"
  },
  "pages": []
}
```

Notes:
- `name` is the project/report title used later in export naming.
- If omitted in the backend, it can fall back to the selected semantic model name.

### 3. Read / Update / Delete project

- `GET /projects/{draft_id}`
- `PATCH /projects/{draft_id}`
- `DELETE /projects/{draft_id}`

Update body:

```json
{
  "name": "Sales",
  "description": "Optional description",
  "source_semantic_model_id": 123,
  "source_semantic_model_name": "Sales",
  "canvas_settings": {
    "width": 1280,
    "height": 720
  },
  "report_settings": {
    "themeName": "BIFoundryTheme",
    "themeColor": "#154360"
  },
  "raw": {}
}
```

### 4. Refresh metadata

- `POST /projects/{draft_id}/metadata-refresh`
- No request body

### 5. Get fields

- `GET /projects/{draft_id}/fields`
- No request body

### 6. Validate

- `POST /projects/{draft_id}/validate`
- No request body

### 7. Pages

#### Create page

- `POST /projects/{draft_id}/pages`

Request body:

```json
{
  "name": "page_1",
  "display_name": "Page 1",
  "width": 1280,
  "height": 720,
  "raw": {},
  "page_order": 0,
  "visuals": []
}
```

#### Update page

- `PATCH /projects/{draft_id}/pages/{page_id}`

Request body:

```json
{
  "name": "page_1",
  "display_name": "Page 1",
  "width": 1280,
  "height": 720,
  "raw": {},
  "page_order": 0
}
```

#### Delete page

- `DELETE /projects/{draft_id}/pages/{page_id}`
- No request body

### 8. Visuals

#### Create visual

- `POST /projects/{draft_id}/pages/{page_id}/visuals`

Request body:

```json
{
  "template_key": "card",
  "name": "KPI",
  "x": 0,
  "y": 0,
  "w": 3,
  "h": 2,
  "bindings": {},
  "config": {},
  "raw": {},
  "visual_order": 0
}
```

#### Update visual

- `PATCH /projects/{draft_id}/pages/{page_id}/visuals/{visual_id}`

Request body:

```json
{
  "template_key": "card",
  "name": "KPI",
  "x": 1,
  "y": 2,
  "w": 4,
  "h": 3,
  "bindings": {},
  "config": {},
  "raw": {},
  "visual_order": 0
}
```

#### Delete visual

- `DELETE /projects/{draft_id}/pages/{page_id}/visuals/{visual_id}`
- No request body

### 9. Compile

- `POST /projects/{draft_id}/compile`
- No request body

Response:
- Returns a ZIP file download.

## Visual Template Import

- `POST /projects/visual-templates/import`
- `multipart/form-data`
- Field name: `archive`

Example:

- key: `archive`
- value: `your-template.zip`

## POC Simplification Notes

If you want the simplest possible POC, collapse the backend into this shape:

1. Keep only `/api/powerbi/*` and `/api/projects/*`.
2. Keep one canonical route per action.
3. Remove or hide alternate compatibility routes after you finish testing.
4. Keep the older `canvas_service.py` code as internal helpers only.
5. Keep request payloads small:
   - project title
   - selected semantic model id
   - canvas size
   - pages
   - visuals

That gives you a much easier Postman workflow and avoids the current duplicated service/module feel.

