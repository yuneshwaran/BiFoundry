from sqlalchemy import select, delete
from models import semantic_models, semantic_model_files, dataset_fields


class SemanticRepo:
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

    def insert_semantic_model(self, **values):
        result = self.conn.execute(semantic_models.insert().values(**values))
        return result.inserted_primary_key[0]

    def get_semantic_model_files(self, semantic_model_id):
        stmt = (
            select(semantic_model_files)
            .where(semantic_model_files.c.semantic_model_id == semantic_model_id)
            .order_by(semantic_model_files.c.relative_path.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def insert_semantic_model_file(self, **values):
        self.conn.execute(semantic_model_files.insert().values(**values))

    def get_dataset_fields(self, dataset_id):
        stmt = (
            select(dataset_fields)
            .where(dataset_fields.c.dataset_id == dataset_id)
            .order_by(dataset_fields.c.table_name.asc(), dataset_fields.c.field_name.asc())
        )
        return [dict(row._mapping) for row in self.conn.execute(stmt)]

    def insert_dataset_field(self, **values):
        result = self.conn.execute(dataset_fields.insert().values(**values))
        return result.inserted_primary_key[0]

    def delete_dataset_fields(self, dataset_id):
        self.conn.execute(delete(dataset_fields).where(dataset_fields.c.dataset_id == dataset_id))
