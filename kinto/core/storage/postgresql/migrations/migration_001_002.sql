ALTER FUNCTION as_epoch(TIMESTAMP) IMMUTABLE;

DROP INDEX IF EXISTS idx_records_last_modified_epoch;
CREATE INDEX idx_records_last_modified_epoch ON records(as_epoch(last_modified));

DROP INDEX IF EXISTS idx_deleted_last_modified_epoch;
CREATE INDEX idx_deleted_last_modified_epoch ON deleted(as_epoch(last_modified));

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '2');
