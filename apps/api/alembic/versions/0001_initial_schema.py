"""Initial Pokédex schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-09
"""

from alembic import op
from pokedex_api.models import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_pokemon_name_trgm "
            "ON pokemon USING gin (lower(name) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_localized_name_name_trgm "
            "ON localized_name USING gin (lower(name) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_localized_name_english_fts "
            "ON localized_name USING gin "
            "(to_tsvector('english', name)) WHERE locale = 'en'"
        )
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_media_asset_pokemon_kind "
            "ON media_asset (pokemon_id, kind) WHERE form_id IS NULL"
        )
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_media_asset_form_kind "
            "ON media_asset (form_id, kind) WHERE form_id IS NOT NULL"
        )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
