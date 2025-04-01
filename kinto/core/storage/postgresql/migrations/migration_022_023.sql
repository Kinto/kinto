CREATE TABLE IF NOT EXISTS objects_partitioned
(
    id text NOT NULL,
    parent_id text NOT NULL,
    resource_name text NOT NULL,
    last_modified timestamp without time zone NOT NULL,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    deleted boolean NOT NULL DEFAULT false,
    CONSTRAINT objects_pkey PRIMARY KEY (id, parent_id, resource_name)
) PARTITION BY LIST(resource_name);

CREATE TABLE objects_default PARTITION OF objects_partitioned 
    FOR VALUES IN ('', 'account', 'bucket', 'collection', 'group');
CREATE TABLE objects_record PARTITION OF objects_partitioned 
    FOR VALUES IN ('record');
CREATE TABLE objects_history PARTITION OF objects_partitioned
    FOR VALUES IN ('history');

INSERT INTO objects_partitioned(id, parent_id, resource_name, last_modified, data, deleted)
SELECT id, parent_id, resource_name, last_modified, data, deleted
FROM objects;

ALTER TABLE objects_partitioned OWNER to kinto;
REVOKE ALL ON TABLE objects_partitioned FROM kinto_ro;
GRANT ALL ON TABLE objects_partitioned TO kinto;
GRANT SELECT ON TABLE objects_partitioned TO kinto_ro;

ALTER TABLE objects RENAME TO objects_old;
ALTER TABLE objects_partitioned RENAME TO objects;

CREATE INDEX IF NOT EXISTS idx_objects_last_modified_epoch_partitioned
    ON objects USING btree
    (as_epoch(last_modified) ASC NULLS LAST);

CREATE UNIQUE INDEX IF NOT EXISTS idx_objects_parent_id_resource_name_last_modified_partitioned
    ON objects USING btree
    (parent_id ASC NULLS LAST, resource_name ASC NULLS LAST, last_modified DESC NULLS FIRST);

CREATE OR REPLACE TRIGGER tgr_objects_last_modified
    BEFORE INSERT OR UPDATE OF data
    ON objects
    FOR EACH ROW
    EXECUTE FUNCTION bump_timestamp();

ALTER INDEX idx_objects_last_modified_epoch RENAME TO idx_objects_last_modified_epoch_old;
ALTER INDEX idx_objects_parent_id_resource_name_last_modified RENAME TO idx_objects_parent_id_resource_name_last_modified_old;
ALTER INDEX idx_objects_last_modified_epoch_partitioned RENAME TO idx_objects_last_modified_epoch;
ALTER INDEX idx_objects_parent_id_resource_name_last_modified_partitioned RENAME TO idx_objects_parent_id_resource_name_last_modified;

CREATE INDEX IF NOT EXISTS idx_objects_resource_name_parent_id_deleted
    ON objects(resource_name, parent_id, deleted);

DROP TABLE objects_old;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '23');
