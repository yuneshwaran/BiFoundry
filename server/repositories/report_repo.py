from sqlalchemy import select, delete, update
from models import canvas_reports, canvas_pages, canvas_visuals


class ReportRepo:
    def __init__(self, conn):
        self.conn = conn

    def get_canvas_reports(self):
        stmt = select(canvas_reports).order_by(canvas_reports.c.id.desc())
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def get_canvas_report(self, canvas_report_id):
        stmt = select(canvas_reports).where(canvas_reports.c.id == canvas_report_id)
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def insert_canvas_report(self, **values):
        result = self.conn.execute(canvas_reports.insert().values(**values))
        return result.inserted_primary_key[0]

    def delete_canvas_report(self, canvas_report_id):
        page_ids = [row._mapping["id"] for row in self.conn.execute(select(canvas_pages.c.id).where(canvas_pages.c.canvas_report_id == canvas_report_id))]
        if page_ids:
            self.conn.execute(delete(canvas_visuals).where(canvas_visuals.c.canvas_page_id.in_(page_ids)))
        self.conn.execute(delete(canvas_pages).where(canvas_pages.c.canvas_report_id == canvas_report_id))
        self.conn.execute(delete(canvas_reports).where(canvas_reports.c.id == canvas_report_id))

    def update_canvas_report(self, canvas_report_id, **values):
        if values:
            self.conn.execute(update(canvas_reports).where(canvas_reports.c.id == canvas_report_id).values(**values))
