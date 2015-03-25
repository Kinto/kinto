ALTER FUNCTION as_epoch(TIMESTAMP) IMMUTABLE;

DROP INDEX IF EXISTS idx_records_last_modified_epoch;
CREATE INDEX idx_records_last_modified_epoch ON records(as_epoch(last_modified));

DROP INDEX IF EXISTS idx_deleted_last_modified_epoch;
CREATE INDEX idx_deleted_last_modified_epoch ON deleted(as_epoch(last_modified));

-- Bump storage schema version.
-- An UPSERT is used since this is the first migration.
-- For future migrations an UPDATE will be used.
WITH upsert AS (
    UPDATE metadata SET value = '2'
    WHERE name = 'storage_schema_version'
    RETURNING *
)
INSERT INTO metadata (name, value)
  SELECT 'storage_schema_version', '2'
   WHERE NOT EXISTS (SELECT * FROM upsert);
