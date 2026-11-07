"""Preserve distinct upstream IDs even when their English identifiers collide."""

from alembic import op

revision = "0005_reference_identifiers"
down_revision = "0004_item_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '60s'")
    for table in ("item", "move", "berry"):
        op.drop_constraint(f"{table}_name_key", table, type_="unique")
        op.create_index(f"ix_{table}_name", table, ["name"])


def downgrade() -> None:
    # A conflicting upstream name must make this downgrade fail atomically, never
    # trigger a merge, rename or deletion. For whole-catalog removal use the
    # explicitly scoped rollback SQL after exporting the newly collected data.
    for table in ("berry", "move", "item"):
        op.drop_index(f"ix_{table}_name", table_name=table)
        op.create_unique_constraint(f"{table}_name_key", table, ["name"])
