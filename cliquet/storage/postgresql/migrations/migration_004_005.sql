CREATE OR REPLACE FUNCTION from_epoch(ts BIGINT) RETURNS TIMESTAMP AS $$
BEGIN
    RETURN to_timestamp(ts / 1000.0) AT TIME ZONE 'UTC';
END;
$$ LANGUAGE plpgsql
IMMUTABLE;


DROP INDEX IF EXISTS idx_records_user_id;
DROP INDEX IF EXISTS idx_records_resource_name;
DROP INDEX IF EXISTS idx_records_last_modified;
DROP INDEX IF EXISTS idx_records_last_modified_epoch;
DROP INDEX IF EXISTS idx_records_id;

ALTER TABLE records
    ADD PRIMARY KEY (id, user_id, resource_name);


DROP INDEX IF EXISTS idx_deleted_id;
DROP INDEX IF EXISTS idx_deleted_user_id;
DROP INDEX IF EXISTS idx_deleted_resource_name;
DROP INDEX IF EXISTS idx_deleted_last_modified;
DROP INDEX IF EXISTS idx_deleted_last_modified_epoch;

ALTER TABLE deleted
    ADD PRIMARY KEY (id, user_id, resource_name);


-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '5');
