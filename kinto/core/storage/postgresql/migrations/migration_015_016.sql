DROP FUNCTION collection_timestamp(uid VARCHAR, resource VARCHAR);

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '16');
