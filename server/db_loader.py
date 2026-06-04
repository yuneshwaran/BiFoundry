from sqlalchemy import delete, select, update

from models import (
    canvas_pages,
    canvas_reports,
    canvas_visuals,
    dataset_fields,
    semantic_model_files,
    semantic_models,
    visual_templates,
)


class DBLoader:
    def __init__(self, conn):
        self.conn = conn

    def insert_semantic_model(self, name, original_filename, semantic_format, semantic_model_folder_name, raw):
        result = self.conn.execute(
            semantic_models.insert().values(
                name=name,
                original_filename=original_filename,
                semantic_format=semantic_format,
                semantic_model_folder_name=semantic_model_folder_name,
                raw=raw,
            )
        )
        return result.inserted_primary_key[0]

    def insert_semantic_model_file(
        self,
        semantic_model_id,
        relative_path,
        artifact_scope,
        content_kind,
        text_content,
        json_content,
        binary_base64,
        sha256,
        size_bytes,
    ):
        self.conn.execute(
            semantic_model_files.insert().values(
                semantic_model_id=semantic_model_id,
                relative_path=relative_path,
                artifact_scope=artifact_scope,
                content_kind=content_kind,
                text_content=text_content,
                json_content=json_content,
                binary_base64=binary_base64,
                sha256=sha256,
                size_bytes=size_bytes,
            )
        )

    def insert_visual_template(
        self,
        template_key,
        name,
        category,
        icon,
        description,
        default_width,
        default_height,
        required_slots,
        optional_slots,
        default_visual_json,
        visual_type=None,
        slot_definitions=None,
        default_format=None,
        is_active="1",
    ):
        visual_type = visual_type or default_visual_json.get("visualType") if isinstance(default_visual_json, dict) else template_key
        if slot_definitions is None:
            slot_definitions = [
                {
                    "name": slot.get("label") or slot.get("key") or slot.get("name"),
                    "role": slot.get("key") or slot.get("name"),
                    "field_type": slot.get("kind") or "any",
                    "required": True,
                    "multi": "list" in str(slot.get("kind") or ""),
                    "description": slot.get("description") or "",
                }
                for slot in (required_slots or [])
            ] + [
                {
                    "name": slot.get("label") or slot.get("key") or slot.get("name"),
                    "role": slot.get("key") or slot.get("name"),
                    "field_type": slot.get("kind") or "any",
                    "required": False,
                    "multi": "list" in str(slot.get("kind") or ""),
                    "description": slot.get("description") or "",
                }
                for slot in (optional_slots or [])
            ]
        result = self.conn.execute(
            visual_templates.insert().values(
                template_key=template_key,
                name=name,
                visual_type=visual_type,
                slot_definitions=slot_definitions,
                default_format=default_format or {},
                is_active=is_active,
                category=category,
                icon=icon,
                description=description,
                default_width=default_width,
                default_height=default_height,
                required_slots=required_slots,
                optional_slots=optional_slots,
                default_visual_json=default_visual_json,
            )
        )
        return result.inserted_primary_key[0]

    def update_visual_template(
        self,
        visual_template_id,
        *,
        template_key=None,
        name=None,
        category=None,
        icon=None,
        description=None,
        default_width=None,
        default_height=None,
        required_slots=None,
        optional_slots=None,
        default_visual_json=None,
        visual_type=None,
        slot_definitions=None,
        default_format=None,
        is_active=None,
    ):
        values = {}
        for key, value in (
            ("template_key", template_key),
            ("name", name),
            ("category", category),
            ("icon", icon),
            ("description", description),
            ("default_width", default_width),
            ("default_height", default_height),
            ("required_slots", required_slots),
            ("optional_slots", optional_slots),
            ("default_visual_json", default_visual_json),
            ("visual_type", visual_type),
            ("slot_definitions", slot_definitions),
            ("default_format", default_format),
            ("is_active", is_active),
        ):
            if value is not None:
                values[key] = value
        if values:
            self.conn.execute(
                update(visual_templates).where(visual_templates.c.id == visual_template_id).values(**values)
            )

    def insert_canvas_report(
        self,
        name,
        description,
        source_semantic_model_id,
        source_semantic_model_name,
        canvas_settings,
        report_settings,
        raw,
        project_id=None,
        settings=None,
        created_at=None,
    ):
        result = self.conn.execute(
            canvas_reports.insert().values(
                name=name,
                project_id=project_id if project_id is not None else source_semantic_model_id,
                settings=settings
                if settings is not None
                else {
                    "theme_color": (report_settings or {}).get("themeColor"),
                    "canvas_width": (canvas_settings or {}).get("width"),
                    "canvas_height": (canvas_settings or {}).get("height"),
                },
                created_at=created_at,
                description=description,
                source_semantic_model_id=source_semantic_model_id,
                source_semantic_model_name=source_semantic_model_name,
                canvas_settings=canvas_settings,
                report_settings=report_settings,
                raw=raw,
            )
        )
        return result.inserted_primary_key[0]

    def insert_canvas_page(self, canvas_report_id, page_order, name, display_name, width, height, raw):
        result = self.conn.execute(
            canvas_pages.insert().values(
                canvas_report_id=canvas_report_id,
                page_name=name,
                page_order=page_order,
                name=name,
                display_name=display_name,
                settings={"width": width, "height": height, "display_option": "FitToPage"},
                width=width,
                height=height,
                raw=raw,
            )
        )
        return result.inserted_primary_key[0]

    def insert_canvas_visual(
        self,
        canvas_page_id,
        visual_order,
        template_key,
        name,
        x,
        y,
        w,
        h,
        bindings,
        config,
        raw,
        visual_template_id=None,
        visual_name=None,
        grid_position=None,
        field_bindings=None,
        format_config=None,
        tab_order=None,
    ):
        result = self.conn.execute(
            canvas_visuals.insert().values(
                canvas_page_id=canvas_page_id,
                visual_template_id=visual_template_id,
                visual_name=visual_name or name,
                grid_position=grid_position
                if grid_position is not None
                else {"col": x, "row": y, "w": w, "h": h},
                field_bindings=field_bindings if field_bindings is not None else bindings,
                format_config=format_config if format_config is not None else config,
                tab_order=tab_order if tab_order is not None else visual_order,
                visual_order=visual_order,
                template_key=template_key,
                name=name,
                x=x,
                y=y,
                w=w,
                h=h,
                bindings=bindings,
                config=config,
                raw=raw,
            )
        )
        return result.inserted_primary_key[0]

    def delete_canvas_report(self, canvas_report_id):
        page_ids = [
            row._mapping["id"]
            for row in self.conn.execute(
                select(canvas_pages.c.id).where(canvas_pages.c.canvas_report_id == canvas_report_id)
            )
        ]
        if page_ids:
            self.conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id.in_(page_ids)))
        self.conn.execute(delete(canvas_pages).where(canvas_pages.c.canvas_report_id == canvas_report_id))
        self.conn.execute(delete(canvas_reports).where(canvas_reports.c.id == canvas_report_id))

    def update_canvas_report(self, canvas_report_id, name=None, settings=None):
        values = {}
        if name is not None:
            values["name"] = name
        if settings is not None:
            values["settings"] = settings
        if values:
            self.conn.execute(
                update(canvas_reports).where(canvas_reports.c.id == canvas_report_id).values(**values)
            )

    def insert_canvas_page_v2(self, canvas_report_id, page_name, display_name, page_order, settings):
        payload = {
            "canvas_report_id": canvas_report_id,
            "page_name": page_name,
            "display_name": display_name,
            "page_order": page_order,
            "settings": settings or {},
            "name": page_name,
            "width": (settings or {}).get("width"),
            "height": (settings or {}).get("height"),
            "raw": {},
        }
        result = self.conn.execute(canvas_pages.insert().values(**payload))
        return result.inserted_primary_key[0]

    def update_canvas_page(self, canvas_page_id, display_name=None, page_order=None, settings=None, page_name=None):
        values = {}
        if display_name is not None:
            values["display_name"] = display_name
        if page_name is not None:
            values["page_name"] = page_name
            values["name"] = page_name
        if page_order is not None:
            values["page_order"] = page_order
        if settings is not None:
            values["settings"] = settings
            values["width"] = settings.get("width")
            values["height"] = settings.get("height")
        if values:
            self.conn.execute(
                update(canvas_pages).where(canvas_pages.c.id == canvas_page_id).values(**values)
            )

    def delete_canvas_page(self, canvas_page_id):
        self.conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id == canvas_page_id))
        self.conn.execute(delete(canvas_pages).where(canvas_pages.c.id == canvas_page_id))

    def insert_canvas_visual_v2(
        self,
        canvas_page_id,
        visual_template_id,
        visual_name,
        grid_position,
        field_bindings,
        format_config,
        tab_order,
    ):
        payload = {
            "canvas_page_id": canvas_page_id,
            "visual_template_id": visual_template_id,
            "visual_name": visual_name,
            "grid_position": grid_position or {},
            "field_bindings": field_bindings or {},
            "format_config": format_config or {},
            "tab_order": tab_order if tab_order is not None else 1000,
            "visual_order": tab_order if tab_order is not None else 1000,
            "template_key": str(visual_template_id),
            "name": visual_name,
            "x": float((grid_position or {}).get("col", 0)),
            "y": float((grid_position or {}).get("row", 0)),
            "w": float((grid_position or {}).get("w", 3)),
            "h": float((grid_position or {}).get("h", 2)),
            "bindings": field_bindings or {},
            "config": format_config or {},
            "raw": {},
        }
        result = self.conn.execute(canvas_visuals.insert().values(**payload))
        return result.inserted_primary_key[0]

    def update_canvas_visual(self, canvas_visual_id, grid_position=None, field_bindings=None, format_config=None, tab_order=None, visual_name=None, name=None):
        values = {}
        if grid_position is not None:
            values["grid_position"] = grid_position
            values["x"] = float(grid_position.get("col", 0))
            values["y"] = float(grid_position.get("row", 0))
            values["w"] = float(grid_position.get("w", 3))
            values["h"] = float(grid_position.get("h", 2))
        if field_bindings is not None:
            values["field_bindings"] = field_bindings
            values["bindings"] = field_bindings
        if format_config is not None:
            values["format_config"] = format_config
            values["config"] = format_config
        if tab_order is not None:
            values["tab_order"] = tab_order
            values["visual_order"] = tab_order
        if visual_name is not None:
            values["visual_name"] = visual_name
        if name is not None:
            values["name"] = name
        if values:
            self.conn.execute(
                update(canvas_visuals).where(canvas_visuals.c.id == canvas_visual_id).values(**values)
            )

    def delete_canvas_visual(self, canvas_visual_id):
        self.conn.execute(delete(canvas_visuals).where(canvas_visuals.c.id == canvas_visual_id))

    def insert_dataset_field(self, dataset_id, table_name, field_name, field_type, data_type, dax_expression):
        result = self.conn.execute(
            dataset_fields.insert().values(
                dataset_id=dataset_id,
                table_name=table_name,
                field_name=field_name,
                field_type=field_type,
                data_type=data_type,
                dax_expression=dax_expression,
            )
        )
        return result.inserted_primary_key[0]

    def delete_dataset_fields(self, dataset_id):
        self.conn.execute(delete(dataset_fields).where(dataset_fields.c.dataset_id == dataset_id))


class DBReader:
    def __init__(self, conn):
        self.conn = conn

    def get_semantic_models(self):
        stmt = select(semantic_models).order_by(semantic_models.c.id.desc())
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_semantic_model(self, semantic_model_id):
        stmt = select(semantic_models).where(semantic_models.c.id == semantic_model_id)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_semantic_model_by_name(self, name):
        stmt = select(semantic_models).where(semantic_models.c.name == name).order_by(semantic_models.c.id.desc())
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_semantic_model_files(self, semantic_model_id):
        stmt = (
            select(semantic_model_files)
            .where(semantic_model_files.c.semantic_model_id == semantic_model_id)
            .order_by(semantic_model_files.c.relative_path.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_semantic_model_files_by_scope(self, semantic_model_id, artifact_scope):
        stmt = (
            select(semantic_model_files)
            .where(semantic_model_files.c.semantic_model_id == semantic_model_id)
            .where(semantic_model_files.c.artifact_scope == artifact_scope)
            .order_by(semantic_model_files.c.relative_path.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_visual_templates(self):
        stmt = select(visual_templates).order_by(visual_templates.c.id.asc())
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_visual_template(self, visual_template_id):
        stmt = select(visual_templates).where(visual_templates.c.id == visual_template_id)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_visual_template_by_key(self, template_key):
        stmt = select(visual_templates).where(visual_templates.c.template_key == template_key)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_canvas_reports(self):
        stmt = select(canvas_reports).order_by(canvas_reports.c.id.desc())
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_canvas_report(self, canvas_report_id):
        stmt = select(canvas_reports).where(canvas_reports.c.id == canvas_report_id)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_canvas_pages(self, canvas_report_id):
        stmt = (
            select(canvas_pages)
            .where(canvas_pages.c.canvas_report_id == canvas_report_id)
            .order_by(canvas_pages.c.page_order.asc(), canvas_pages.c.id.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_canvas_page(self, canvas_page_id):
        stmt = select(canvas_pages).where(canvas_pages.c.id == canvas_page_id)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_canvas_visuals(self, canvas_page_id):
        stmt = (
            select(canvas_visuals)
            .where(canvas_visuals.c.canvas_page_id == canvas_page_id)
            .order_by(canvas_visuals.c.visual_order.asc(), canvas_visuals.c.id.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_canvas_visual(self, canvas_visual_id):
        stmt = select(canvas_visuals).where(canvas_visuals.c.id == canvas_visual_id)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_dataset_fields(self, dataset_id):
        stmt = (
            select(dataset_fields)
            .where(dataset_fields.c.dataset_id == dataset_id)
            .order_by(dataset_fields.c.table_name.asc(), dataset_fields.c.field_name.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]
