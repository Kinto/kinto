ALTER TABLE records ADD COLUMN deleted BOOLEAN;

-- XXX LOCK TABLES ?

INSERT INTO records (id, parent_id, collection_id, data, deleted)
  SELECT id, parent_id, collection_id, '{"deleted": true}'::JSONB, TRUE
  FROM deleted;

DROP TABLE deleted CASCADE;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '18');
