-- PREPARED ONLY: export newly collected data before an explicitly requested rollback.
-- Removes only the 18 new catalog tables; retains all original tables, sources and media.
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='60s';
DO $$ BEGIN
  IF (SELECT version_num FROM alembic_version) IS DISTINCT FROM '0005_reference_identifiers' THEN
    RAISE EXCEPTION 'Unexpected schema revision; review rollback before execution';
  END IF;
END $$;
DROP TABLE "berry_flavor_link";
DROP TABLE "pokemon_move";
DROP TABLE "pokemon_held_item";
DROP TABLE "move_stat_change";
DROP TABLE "move_past_value";
DROP TABLE "item_price";
DROP TABLE "item_game_index";
DROP TABLE "item_attribute_link";
DROP TABLE "evolution_item_reference";
DROP TABLE "catalog_machine";
DROP TABLE "berry";
DROP TABLE "move";
DROP TABLE "item";
DROP TABLE "catalog_dictionary_link";
DROP TABLE "catalog_sync_entry";
DROP TABLE "catalog_discovery_page";
DROP TABLE "catalog_dictionary";
DROP TABLE "catalog_reference_issue";
UPDATE alembic_version SET version_num='0002_version_sprites';
COMMIT;
