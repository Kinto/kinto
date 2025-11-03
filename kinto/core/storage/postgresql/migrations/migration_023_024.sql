CREATE INDEX idx_objects_history_userid_and_resourcename
  ON objects ((data->'user_id'), (data->'resource_name'))
  WHERE resource_name = 'history';

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '24');
