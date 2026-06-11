from sqlalchemy import select, update, delete
from models import canvas_pages, canvas_visuals


class PageRepo:
    def __init__(self, conn):
        self.conn = conn

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

    def insert_canvas_page(self, **values):
        result = self.conn.execute(canvas_pages.insert().values(**values))
        return result.inserted_primary_key[0]

    def insert_canvas_page_v2(self, **values):
        result = self.conn.execute(canvas_pages.insert().values(**values))
        return result.inserted_primary_key[0]

    def update_canvas_page(self, canvas_page_id, **values):
        if values:
            # ensure width/height sync when settings provided is handled by caller
            self.conn.execute(update(canvas_pages).where(canvas_pages.c.id == canvas_page_id).values(**values))

    def delete_canvas_page(self, canvas_page_id):
        self.conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id == canvas_page_id))
        self.conn.execute(delete(canvas_pages).where(canvas_pages.c.id == canvas_page_id))
