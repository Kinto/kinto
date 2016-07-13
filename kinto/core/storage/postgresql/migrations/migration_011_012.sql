-- Select all existing records and delete their tombstone if any.
DELETE FROM deleted d
USING records r
WHERE d.id = r.id
AND   d.parent_id = r.parent_id
AND   d.collection_id = r.collection_id;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '12');
