CREATE INDEX IF NOT EXISTS idx_objects_parent_id_record_last_modified
    ON objects (parent_id, last_modified DESC)
    WHERE resource_name = 'record';

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '25');
