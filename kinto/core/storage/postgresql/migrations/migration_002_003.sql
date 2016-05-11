ALTER TABLE records DROP CONSTRAINT records_id_user_id_resource_name_last_modified_key CASCADE;
CREATE UNIQUE INDEX idx_records_user_id_resource_name_last_modified
    ON records(user_id, resource_name, last_modified DESC);

ALTER TABLE deleted DROP CONSTRAINT deleted_id_user_id_resource_name_last_modified_key CASCADE;
CREATE UNIQUE INDEX idx_deleted_user_id_resource_name_last_modified
    ON deleted(user_id, resource_name, last_modified DESC);

CREATE OR REPLACE FUNCTION resource_timestamp(uid VARCHAR, resource VARCHAR)
RETURNS TIMESTAMP AS $$
DECLARE
    ts_records TIMESTAMP;
    ts_deleted TIMESTAMP;
BEGIN
    SELECT last_modified INTO ts_records
      FROM records
     WHERE user_id = uid
       AND resource_name = resource
     ORDER BY last_modified DESC LIMIT 1;

    SELECT last_modified INTO ts_deleted
      FROM deleted
     WHERE user_id = uid
       AND resource_name = resource
     ORDER BY last_modified DESC LIMIT 1;

    -- Latest of records/deleted or current if empty
    RETURN coalesce(greatest(ts_deleted, ts_records), localtimestamp);
END;
$$ LANGUAGE plpgsql;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '3');
