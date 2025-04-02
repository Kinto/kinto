CREATE INDEX IF NOT EXISTS idx_objects_resource_name_parent_id_deleted
    ON objects(resource_name, parent_id, deleted);

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '23');
