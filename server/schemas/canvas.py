from pydantic import BaseModel, Field, AliasChoices, ConfigDict


class VisualTemplateOut(BaseModel):
    id: int
    template_key: str
    name: str
    category: str | None = None
    icon: str | None = None
    description: str | None = None
    default_width: int | None = None
    default_height: int | None = None
    slot_definitions: list[dict] = Field(default_factory=list)
    required_slots: list[dict] = Field(default_factory=list)
    optional_slots: list[dict] = Field(default_factory=list)
    default_visual_json: dict = Field(default_factory=dict)


class CanvasVisualBase(BaseModel):
    template_key: str
    name: str | None = None
    x: int = 0
    y: int = 0
    w: int = 3
    h: int = 2
    bindings: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)
    raw: dict = Field(default_factory=dict)


class CanvasVisualCreate(CanvasVisualBase):
    id: int | None = None
    visual_order: int = 0


class CanvasVisualUpdate(BaseModel):
    template_key: str | None = None
    name: str | None = None
    x: int | None = None
    y: int | None = None
    w: int | None = None
    h: int | None = None
    bindings: dict | None = None
    config: dict | None = None
    raw: dict | None = None
    visual_order: int | None = None


class CanvasPageBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(validation_alias=AliasChoices("name", "page_name"))
    display_name: str | None = None
    width: int = 1280
    height: int = 720
    raw: dict = Field(default_factory=dict)


class CanvasPageCreate(CanvasPageBase):
    id: int | None = None
    page_order: int = 0
    visuals: list[CanvasVisualCreate] = Field(default_factory=list)


class CanvasPageUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "page_name"))
    display_name: str | None = None
    width: int | None = None
    height: int | None = None
    raw: dict | None = None
    page_order: int | None = None


class CanvasReportCreate(BaseModel):
    name: str
    description: str | None = None
    source_semantic_model_id: int
    source_semantic_model_name: str | None = None
    canvas_settings: dict = Field(default_factory=dict)
    report_settings: dict = Field(default_factory=dict)
    raw: dict = Field(default_factory=dict)
    pages: list[CanvasPageCreate] = Field(default_factory=list)


class CanvasReportUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    source_semantic_model_id: int | None = None
    source_semantic_model_name: str | None = None
    canvas_settings: dict | None = None
    report_settings: dict | None = None
    raw: dict | None = None


class CanvasReportSnapshot(BaseModel):
    name: str | None = None
    description: str | None = None
    source_semantic_model_id: int | None = None
    source_semantic_model_name: str | None = None
    canvas_settings: dict | None = None
    report_settings: dict | None = None
    raw: dict | None = None
    pages: list[CanvasPageCreate] = Field(default_factory=list)


class FieldOption(BaseModel):
    table: str
    name: str
    kind: str
    data_type: str | None = None
    label: str | None = None


class FieldGroup(BaseModel):
    table: str
    fields: list[FieldOption] = Field(default_factory=list)


class SemanticFieldResponse(BaseModel):
    source_semantic_model_id: int
    source_semantic_model_name: str
    tables: list[FieldGroup] = Field(default_factory=list)
    fields: list[FieldOption] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)


class CanvasReportOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    source_semantic_model_id: int | None = None
    source_semantic_model_name: str | None = None
    canvas_settings: dict = Field(default_factory=dict)
    report_settings: dict = Field(default_factory=dict)
    raw: dict = Field(default_factory=dict)
    pages: list[dict] = Field(default_factory=list)


class CompileResponse(BaseModel):
    message: str
    report_id: int
    filename: str
