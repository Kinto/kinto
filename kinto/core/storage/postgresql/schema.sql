--
-- Automated script, we do not need NOTICE and WARNING
--
SET client_min_messages TO ERROR;
--
-- Convert timestamps to milliseconds epoch integer
--
CREATE OR REPLACE FUNCTION as_epoch(ts TIMESTAMP) RETURNS BIGINT AS $$
BEGIN
    RETURN (EXTRACT(EPOCH FROM ts) * 1000)::BIGINT;
END;
$$ LANGUAGE plpgsql
IMMUTABLE;

CREATE OR REPLACE FUNCTION from_epoch(epoch BIGINT) RETURNS TIMESTAMP AS $$
BEGIN
    RETURN TIMESTAMP WITH TIME ZONE 'epoch' + epoch * INTERVAL '1 millisecond';
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_records_parent_id_collection_id_last_modified
    ON records(parent_id, collection_id, last_modified DESC);
CREATE INDEX IF NOT EXISTS idx_records_last_modified_epoch
    ON records(as_epoch(last_modified));

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
CREATE UNIQUE INDEX IF NOT EXISTS idx_deleted_parent_id_collection_id_last_modified
  ON deleted(parent_id, collection_id, last_modified DESC);
CREATE INDEX IF NOT EXISTS idx_deleted_last_modified_epoch
  ON deleted(as_epoch(last_modified));


CREATE TABLE IF NOT EXISTS timestamps (
  parent_id TEXT NOT NULL,
  collection_id TEXT NOT NULL,
  last_modified TIMESTAMP NOT NULL,
  PRIMARY KEY (parent_id, collection_id)
);


--
-- Helper that returns the current collection timestamp.
--
CREATE OR REPLACE FUNCTION collection_timestamp(uid VARCHAR, resource VARCHAR)
RETURNS TIMESTAMP AS $$
DECLARE
    ts TIMESTAMP;
BEGIN
    ts := NULL;

    SELECT last_modified INTO ts
      FROM timestamps
     WHERE parent_id = uid
       AND collection_id = resource;

    IF ts IS NULL THEN
      ts := clock_timestamp();
      INSERT INTO timestamps (parent_id, collection_id, last_modified)
      VALUES (uid, resource, ts);
    END IF;

    RETURN ts;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION find_timestamp(pid VARCHAR, cid VARCHAR, ts TIMESTAMP)
RETURNS TIMESTAMP AS $$
DECLARE
    previous_collection_ts TIMESTAMP;
    record_ts TIMESTAMP;
BEGIN
	record_ts := ts;

	previous_collection_ts := NULL;
    SELECT last_modified INTO previous_collection_ts
      FROM timestamps
     WHERE parent_id = pid
       AND collection_id = cid;

    IF ts IS NULL OR
       (previous_collection_ts IS NOT NULL AND as_epoch(ts) = as_epoch(previous_collection_ts)) THEN
        -- If record does not carry last-modified, or if the one specified
        -- is equal to previous, assign it to current (i.e. bump it).
	  record_ts := previous_collection_ts;
	END IF;
RETURN record_ts;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION bump_timestamp(pid VARCHAR, cid VARCHAR, ts TIMESTAMP)
RETURNS TIMESTAMP AS $$
DECLARE
    previous_collection_ts TIMESTAMP;
    next_collection_ts TIMESTAMP;
    record_ts TIMESTAMP;
BEGIN
	record_ts := ts;

    previous_collection_ts := NULL;
    SELECT last_modified INTO previous_collection_ts
      FROM timestamps
     WHERE parent_id = pid
       AND collection_id = cid;

    --
    -- This bumps the current timestamp to 1 msec in the future if the previous
    -- timestamp is equal to the current one (or higher if was bumped already).
    --
    -- If a bunch of requests from the same user on the same collection
    -- arrive in the same millisecond, the unicity constraint can raise
    -- an error (operation is cancelled).
    -- See https://github.com/mozilla-services/cliquet/issues/25
    --
    next_collection_ts := clock_timestamp();
    IF previous_collection_ts IS NOT NULL AND previous_collection_ts >= next_collection_ts THEN
        next_collection_ts := previous_collection_ts + INTERVAL '1 milliseconds';
    END IF;

    IF ts IS NULL OR
       (previous_collection_ts IS NOT NULL AND as_epoch(ts) = as_epoch(previous_collection_ts)) THEN
        -- If record does not carry last-modified, or if the one specified
        -- is equal to previous, assign it to current (i.e. bump it).
		record_ts := next_collection_ts;
    ELSE
        -- Use record last-modified as collection timestamp.
        IF previous_collection_ts IS NULL OR ts > previous_collection_ts THEN
            next_collection_ts := ts;
        END IF;
    END IF;

    --
    -- Upsert current collection timestamp.
    --
    INSERT INTO timestamps (parent_id, collection_id, last_modified)
    VALUES (pid, cid, next_collection_ts)
	ON CONFLICT (parent_id, collection_id) DO UPDATE
	  SET last_modified = next_collection_ts;

    RETURN record_ts;
END;
$$ LANGUAGE plpgsql;


--
-- Triggers to set last_modified on INSERT/UPDATE
--
DROP TRIGGER IF EXISTS tgr_records_last_modified ON records;
DROP TRIGGER IF EXISTS tgr_deleted_last_modified ON deleted;


CREATE OR REPLACE FUNCTION bump_timestamp()
RETURNS trigger AS $$
BEGIN
    NEW.last_modified := bump_timestamp(NEW.parent_id, NEW.collection_id, NEW.last_modified);
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_records_last_modified
BEFORE INSERT OR UPDATE OF data ON records
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

CREATE TRIGGER tgr_deleted_last_modified
BEFORE INSERT ON deleted
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
-- Should match ``kinto.core.storage.postgresql.PostgreSQL.schema_version``
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '14');
