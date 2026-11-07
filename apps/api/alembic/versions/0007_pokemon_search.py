"""Versioned Pokémon search snapshots and database-wide cache invalidation."""

from alembic import op

revision = "0007_pokemon_search"
down_revision = "0006_item_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep revision discovery compatible with older running API containers.
    # Only executing the migration requires the matching application models.
    from pokedex_api.models import PokemonSearchIndex, PokemonSearchVersion
    from pokedex_api.search_schema import install_search_versioning

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout='5s'")
        op.execute("SET LOCAL statement_timeout='60s'")
    PokemonSearchVersion.__table__.create(bind, checkfirst=True)
    PokemonSearchIndex.__table__.create(bind, checkfirst=True)
    install_search_versioning(None, bind)


def downgrade() -> None:
    from pokedex_api.models import PokemonSearchIndex, PokemonSearchVersion
    from pokedex_api.search_schema import SOURCE_TABLES

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in SOURCE_TABLES:
            op.execute(f"DROP TRIGGER IF EXISTS pokemon_search_changed ON {table}")
        op.execute("DROP FUNCTION IF EXISTS invalidate_pokemon_search()")
    else:
        for table in SOURCE_TABLES:
            for operation in ("insert", "update", "delete"):
                op.execute(f"DROP TRIGGER IF EXISTS search_{table}_{operation}")
    PokemonSearchIndex.__table__.drop(bind)
    PokemonSearchVersion.__table__.drop(bind)
