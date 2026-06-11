from sqlalchemy import select, update, delete
from models import canvas_visuals


class VisualRepo:
    def __init__(self, conn):
        self.conn = conn

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

    def insert_canvas_visual(self, **values):
        result = self.conn.execute(canvas_visuals.insert().values(**values))
        return result.inserted_primary_key[0]

    def insert_canvas_visual_v2(self, **values):
        result = self.conn.execute(canvas_visuals.insert().values(**values))
        return result.inserted_primary_key[0]

    def update_canvas_visual(self, canvas_visual_id, **values):
        if values:
            self.conn.execute(update(canvas_visuals).where(canvas_visuals.c.id == canvas_visual_id).values(**values))

    def delete_canvas_visual(self, canvas_visual_id):
        self.conn.execute(delete(canvas_visuals).where(canvas_visuals.c.id == canvas_visual_id))
