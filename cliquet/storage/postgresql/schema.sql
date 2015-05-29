--
-- Convert timestamps to milliseconds epoch integer
--
CREATE OR REPLACE FUNCTION as_epoch(ts TIMESTAMP) RETURNS BIGINT AS $$
BEGIN
    RETURN (EXTRACT(EPOCH FROM ts) * 1000)::BIGINT;
END;
$$ LANGUAGE plpgsql
IMMUTABLE;

--
-- Actual records
--
CREATE TABLE IF NOT EXISTS records (
    id TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    collection_id TEXT NOT NULL,

    -- Timestamp is relevant because adequate semantically.
    -- Since the HTTP API manipulates integers, it could make sense
    -- to replace the timestamp columns type by integer.
    last_modified TIMESTAMP NOT NULL,

    -- JSONB, 2x faster than JSON.
    data JSONB NOT NULL DEFAULT '{}'::JSONB,

    PRIMARY KEY (id, parent_id, collection_id)
);

DROP INDEX IF EXISTS idx_records_parent_id_collection_id_last_modified;
CREATE UNIQUE INDEX idx_records_parent_id_collection_id_last_modified
    ON records(parent_id, collection_id, last_modified DESC);
DROP INDEX IF EXISTS idx_records_last_modified_epoch;
CREATE INDEX idx_records_last_modified_epoch ON records(as_epoch(last_modified));


--
-- Deleted records, without data.
--
CREATE TABLE IF NOT EXISTS deleted (
    id TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    collection_id TEXT NOT NULL,
    last_modified TIMESTAMP NOT NULL,

    PRIMARY KEY (id, parent_id, collection_id)
);
DROP INDEX IF EXISTS idx_deleted_parent_id_collection_id_last_modified;
CREATE UNIQUE INDEX idx_deleted_parent_id_collection_id_last_modified
    ON deleted(parent_id, collection_id, last_modified DESC);
DROP INDEX IF EXISTS idx_deleted_last_modified_epoch;
CREATE INDEX idx_deleted_last_modified_epoch ON deleted(as_epoch(last_modified));


--
-- Helper that returns the current collection timestamp.
--
CREATE OR REPLACE FUNCTION collection_timestamp(uid VARCHAR, resource VARCHAR)
RETURNS TIMESTAMP AS $$
DECLARE
    ts_records TIMESTAMP;
    ts_deleted TIMESTAMP;
BEGIN
    --
    -- This is fast because an index was created for ``parent_id``,
    -- ``collection_id``, and ``last_modified`` with descending sorting order.
    --
    SELECT last_modified INTO ts_records
      FROM records
     WHERE parent_id = uid
       AND collection_id = resource
     ORDER BY last_modified DESC LIMIT 1;

    SELECT last_modified INTO ts_deleted
      FROM deleted
     WHERE parent_id = uid
       AND collection_id = resource
     ORDER BY last_modified DESC LIMIT 1;

    -- Latest of records/deleted or current if empty
    RETURN coalesce(greatest(ts_deleted, ts_records), localtimestamp);
END;
$$ LANGUAGE plpgsql;

--
-- Triggers to set last_modified on INSERT/UPDATE
--
DROP TRIGGER IF EXISTS tgr_records_last_modified ON records;
DROP TRIGGER IF EXISTS tgr_deleted_last_modified ON deleted;

CREATE OR REPLACE FUNCTION bump_timestamp()
RETURNS trigger AS $$
DECLARE
    previous TIMESTAMP;
    current TIMESTAMP;
BEGIN
    --
    -- This bumps the current timestamp to 1 msec in the future if the previous
    -- timestamp is equal to the current one (or higher if was bumped already).
    --
    -- If a bunch of requests from the same user on the same collection
    -- arrive in the same millisecond, the unicity constraint can raise
    -- an error (operation is cancelled).
    -- See https://github.com/mozilla-services/cliquet/issues/25
    --
    previous := collection_timestamp(NEW.parent_id, NEW.collection_id);
    current := localtimestamp;

    IF previous >= current THEN
        current := previous + INTERVAL '1 milliseconds';
    END IF;

    NEW.last_modified := current;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_records_last_modified
BEFORE INSERT OR UPDATE ON records
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

CREATE TRIGGER tgr_deleted_last_modified
BEFORE INSERT OR UPDATE ON deleted
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

--
-- Metadata table
--
CREATE TABLE IF NOT EXISTS metadata (
    name VARCHAR(128) NOT NULL,
    value VARCHAR(512) NOT NULL
);
INSERT INTO metadata (name, value) VALUES ('created_at', NOW()::TEXT);


-- Set storage schema version.
-- Should match ``cliquet.storage.postgresql.PostgreSQL.schema_version``
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '7');
