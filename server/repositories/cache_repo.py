from sqlalchemy import select, delete
from models import project_semantic_model_cache


class CacheRepo:
    def __init__(self, conn):
        self.conn = conn

    def latest_project_cache(self, project_id):
        stmt = (
            select(project_semantic_model_cache)
            .where(project_semantic_model_cache.c.project_id == project_id)
            .order_by(project_semantic_model_cache.c.cache_version.desc())
            .limit(1)
        )
        row = self.conn.execute(stmt).first()
        return dict(row._mapping) if row else None

    def insert_project_cache(self, **values):
        result = self.conn.execute(project_semantic_model_cache.insert().values(**values))
        return result.inserted_primary_key[0]

    def delete_by_project(self, project_id):
        self.conn.execute(delete(project_semantic_model_cache).where(project_semantic_model_cache.c.project_id == project_id))

    def delete_by_semantic_model_ids(self, semantic_model_ids):
        self.conn.execute(delete(project_semantic_model_cache).where(project_semantic_model_cache.c.semantic_model_row_id.in_(semantic_model_ids)))
