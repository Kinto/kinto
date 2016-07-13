-- Select all existing records and delete their tombstone if any.
DELETE FROM deleted d
WHERE (d.id, d.parent_id, d.collection_id) IN
  (SELECT r.id, r.parent_id, r.collection_id FROM records r);

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '12');
