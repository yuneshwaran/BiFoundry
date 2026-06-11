from sqlalchemy import select, update
from models import visual_templates


class TemplateRepo:
    def __init__(self, conn):
        self.conn = conn

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

    def insert_visual_template(self, **values):
        result = self.conn.execute(visual_templates.insert().values(**values))
        return result.inserted_primary_key[0]

    def update_visual_template(self, visual_template_id, **values):
        if values:
            self.conn.execute(update(visual_templates).where(visual_templates.c.id == visual_template_id).values(**values))
