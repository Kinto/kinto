-- Add new deleted column (split into commands is more efficient)
ALTER TABLE records ADD COLUMN deleted BOOLEAN;
UPDATE records SET deleted = FALSE;
ALTER TABLE records ALTER COLUMN deleted SET NOT NULL;
ALTER TABLE records ALTER COLUMN deleted SET DEFAULT FALSE;


-- Lock records and deleted tables before merging them.
BEGIN WORK;
LOCK TABLE records IN ACCESS EXCLUSIVE MODE;
LOCK TABLE deleted IN ACCESS EXCLUSIVE MODE;

INSERT INTO records (id, parent_id, collection_id, data, last_modified, deleted)
  SELECT id, parent_id, collection_id, '{"deleted": true}'::JSONB, last_modified, TRUE
  FROM deleted
-- Because of Bug Kinto/kinto#1375, some tombstones may exist.
  ON CONFLICT (id, parent_id, collection_id) DO NOTHING;
COMMIT WORK;
-- Table merged.

-- We do not drop the `deleted` table here.
-- It can be dropped manually once Web heads run the appropriate Kinto version.

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '18');
