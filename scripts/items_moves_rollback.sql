-- Prepared only. Stop the new UI/API code before a requested schema rollback.
-- All pre-existing tables and files remain intact; shared files must never be deleted here.
BEGIN;
SET LOCAL lock_timeout='5s';
DO $$ BEGIN
  IF (SELECT version_num FROM alembic_version) IS DISTINCT FROM '0006_item_media' THEN
    RAISE EXCEPTION 'Unexpected revision; review rollback';
  END IF;
END $$;
DROP TABLE item_media;
UPDATE alembic_version SET version_num='0005_reference_identifiers';
COMMIT;
