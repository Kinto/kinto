--
-- Switch records data column to JSONB.
-- (requires PostgreSQL 9.4+)
--
ALTER TABLE records
    ALTER COLUMN data DROP DEFAULT,
    ALTER COLUMN data SET DATA TYPE JSONB USING data::TEXT::JSONB,
    ALTER COLUMN data SET DEFAULT '{}'::JSONB;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '6');
