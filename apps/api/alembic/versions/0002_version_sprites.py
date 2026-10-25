"""Store each historical sprite source field and deduplicated local file reference."""

import sqlalchemy as sa

from alembic import op

revision = "0002_version_sprites"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The long-running historical media import may create this table before the
    # Docker API image is rebuilt. Alembic still needs to record this revision.
    if "version_sprite" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "version_sprite",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_type", sa.String(12), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("generation", sa.String(32), nullable=False),
        sa.Column("game", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("format", sa.String(8), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("owner_type", "owner_id", "generation", "game", "kind"),
    )
    op.create_index("ix_version_sprite_owner", "version_sprite", ["owner_type", "owner_id"])
    op.create_index("ix_version_sprite_source_url", "version_sprite", ["source_url"])
    op.create_index("ix_version_sprite_status", "version_sprite", ["status"])
    op.create_index("ix_version_sprite_checksum", "version_sprite", ["checksum"])


def downgrade() -> None:
    op.drop_table("version_sprite")
