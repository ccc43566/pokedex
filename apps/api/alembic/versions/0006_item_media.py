"""Keep default item images separate while sharing existing SHA-256 files."""

import sqlalchemy as sa

from alembic import op

revision = "0006_item_media"
down_revision = "0005_reference_identifiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("SET LOCAL statement_timeout='60s'")
    op.create_table(
        "item_media",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), primary_key=True),
        sa.Column("source_url", sa.Text()),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("checksum", sa.String(64)),
        sa.Column("local_path", sa.Text()),
        sa.Column("format", sa.String(8)),
        sa.Column("byte_size", sa.Integer()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("frame_count", sa.Integer()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in ("source_url", "status", "checksum"):
        op.create_index(f"ix_item_media_{column}", "item_media", [column])


def downgrade() -> None:
    # Files remain intact: their hashes may also be used by Pokemon or other items.
    op.drop_table("item_media")
