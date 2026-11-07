"""Store current upstream version/currency item prices without collapsing nulls."""

from alembic import op

revision = "0004_item_prices"
down_revision = "0003_reference_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("SET LOCAL statement_timeout = '60s'")
    op.execute("""
        CREATE TABLE item_price (
        id SERIAL NOT NULL,
        item_id INTEGER NOT NULL,
        ordinal INTEGER NOT NULL,
        version_group_id INTEGER NOT NULL,
        currency_id INTEGER NOT NULL,
        purchase_price INTEGER,
        sell_price INTEGER,
        raw_payload JSONB NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (item_id, ordinal),
        FOREIGN KEY(item_id) REFERENCES item (id),
        FOREIGN KEY(version_group_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(currency_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_item_price_currency_id ON item_price (currency_id)
    """)
    op.execute("""
        CREATE INDEX ix_item_price_item_id ON item_price (item_id)
    """)
    op.execute("""
        CREATE INDEX ix_item_price_purchase_price ON item_price (purchase_price)
    """)
    op.execute("""
        CREATE INDEX ix_item_price_sell_price ON item_price (sell_price)
    """)
    op.execute("""
        CREATE INDEX ix_item_price_version_group_id ON item_price (version_group_id)
    """)


def downgrade() -> None:
    op.drop_table("item_price")
