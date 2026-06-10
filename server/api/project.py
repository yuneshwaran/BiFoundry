from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from schemas.canvas import (
    CanvasPageCreate,
    CanvasPageUpdate,
    CanvasReportCreate,
    CanvasReportUpdate,
    CanvasVisualCreate,
    CanvasVisualUpdate,
)
from services.project_service import (
    cleanup_compile_output,
    compile_draft,
    create_draft,
    create_page,
    create_visual,
    delete_draft,
    delete_page,
    delete_visual,
    get_draft_detail,
    get_draft_fields,
    list_drafts,
    refresh_project_metadata,
    update_draft,
    update_page,
    update_visual,
    validate_draft,
)
from visuals import list_visual_definitions

router = APIRouter(tags=["project"])


@router.get("/projects")
def list_drafts_route():
    return list_drafts()


@router.get("/projects/visual-templates")
def list_visual_templates_route():
    return list_visual_definitions()


@router.post("/projects/visual-templates/import")
def import_visual_templates_route():
    raise HTTPException(
        status_code=409,
        detail="PBIP template import is disabled while the code-first visual registry is active.",
    )

@router.post("/projects")
def create_draft_route(payload: CanvasReportCreate):
    return create_draft(payload)




@router.patch("/projects/{draft_id}")
def update_draft_route(draft_id: int, payload: CanvasReportUpdate):
    return update_draft(draft_id, payload)


@router.delete("/projects/{draft_id}")
def delete_draft_route(draft_id: int):
    return delete_draft(draft_id)


@router.post("/projects/{draft_id}/metadata-refresh")
def sync_metadata_route(draft_id: int):
    return refresh_project_metadata(draft_id)


@router.get("/projects/{draft_id}/fields")
def get_fields_route(draft_id: int):
    return get_draft_fields(draft_id)

@router.get("/projects/{draft_id}")
def get_draft_route(draft_id: int):
    return get_draft_detail(draft_id)

@router.post("/projects/{draft_id}/validate")
def validate_draft_route(draft_id: int):
    return validate_draft(draft_id)


@router.post("/projects/{draft_id}/pages")
def create_page_route(draft_id: int, payload: CanvasPageCreate):
    return create_page(draft_id, payload)


@router.patch("/projects/{draft_id}/pages/{page_id}")
def update_page_route(draft_id: int, page_id: int, payload: CanvasPageUpdate):
    return update_page(page_id, payload)


@router.delete("/projects/{draft_id}/pages/{page_id}")
def delete_page_route(draft_id: int, page_id: int):
    return delete_page(page_id)


@router.post("/projects/{draft_id}/pages/{page_id}/visuals")
def create_visual_route(draft_id: int, page_id: int, payload: CanvasVisualCreate):
    return create_visual(page_id, payload)


@router.patch("/projects/{draft_id}/pages/{page_id}/visuals/{visual_id}")
def update_visual_route(draft_id: int, page_id: int, visual_id: int, payload: CanvasVisualUpdate):
    return update_visual(visual_id, payload)


@router.delete("/projects/{draft_id}/pages/{page_id}/visuals/{visual_id}")
def delete_visual_route(draft_id: int, page_id: int, visual_id: int):
    return delete_visual(visual_id)


@router.post("/projects/{draft_id}/compile")
def compile_draft_route(draft_id: int):
    archive_path, archive_name, compile_root = compile_draft(draft_id)
    return FileResponse(
        path=archive_path,
        filename=archive_name,
        media_type="application/zip",
        background=BackgroundTask(cleanup_compile_output, compile_root, archive_path),
    )
