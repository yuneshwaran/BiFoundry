from sqlalchemy import select

from models import (
    canvas_pages,
    canvas_reports,
    canvas_visuals,
    dataset_fields,
    semantic_model_files,
    semantic_models,
    visual_templates,
)


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
