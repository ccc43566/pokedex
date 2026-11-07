"""Database-owned invalidation shared by API workers, sync jobs and direct SQL edits."""

from typing import Any

from sqlalchemy import Connection, MetaData, text

SOURCE_TABLES = (
    "pokemon",
    "pokemon_species",
    "pokemon_form",
    "pokemon_ability",
    "ability",
    "localized_name",
    "pokemon_type",
    "type",
    "media_asset",
)


def install_search_versioning(
    metadata: MetaData | None,
    connection: Connection,
    **kwargs: Any,
) -> None:
    dialect = connection.dialect.name
    random_version = (
        "md5(random()::text || clock_timestamp()::text)"
        if dialect == "postgresql"
        else "lower(hex(randomblob(16)))"
    )
    connection.execute(
        text(
            "INSERT INTO pokemon_search_version (id, version) "
            f"VALUES (1, {random_version}) ON CONFLICT (id) DO NOTHING"
        )
    )
    if dialect == "postgresql":
        connection.execute(
            text("""
            CREATE OR REPLACE FUNCTION invalidate_pokemon_search() RETURNS trigger AS $$
            BEGIN
                UPDATE pokemon_search_version
                SET version = md5(random()::text || clock_timestamp()::text) WHERE id = 1;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql
        """)
        )
        for table in SOURCE_TABLES:
            connection.execute(text(f"DROP TRIGGER IF EXISTS pokemon_search_changed ON {table}"))
            connection.execute(
                text(
                    f"CREATE TRIGGER pokemon_search_changed AFTER INSERT OR UPDATE OR DELETE "
                    f"OR TRUNCATE ON {table} FOR EACH STATEMENT "
                    "EXECUTE FUNCTION invalidate_pokemon_search()"
                )
            )
    elif dialect == "sqlite":
        for table in SOURCE_TABLES:
            for operation in ("INSERT", "UPDATE", "DELETE"):
                connection.execute(
                    text(
                        f"CREATE TRIGGER IF NOT EXISTS search_{table}_{operation.lower()} "
                        f'AFTER {operation} ON "{table}" BEGIN '
                        "UPDATE pokemon_search_version SET version = lower(hex(randomblob(16))) "
                        "WHERE id = 1; END"
                    )
                )
