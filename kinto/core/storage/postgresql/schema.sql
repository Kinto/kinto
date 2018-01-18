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
    -- These are all IDs stored as text, and not human language.
    -- Therefore, we store them in the C collation. This lets Postgres
    -- use the index on parent_id for prefix matching (parent_id LIKE
    -- '/buckets/abc/%').
    id TEXT COLLATE "C" NOT NULL,
    parent_id TEXT COLLATE "C" NOT NULL,
    collection_id TEXT COLLATE "C" NOT NULL,

    -- Timestamp is relevant because adequate semantically.
    -- Since the HTTP API manipulates integers, it could make sense
    -- to replace the timestamp columns type by integer.
    last_modified TIMESTAMP NOT NULL,

    -- JSONB, 2x faster than JSON.
    data JSONB NOT NULL DEFAULT '{}'::JSONB,

    deleted BOOLEAN NOT NULL,

    PRIMARY KEY (id, parent_id, collection_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_records_parent_id_collection_id_last_modified
    ON records(parent_id, collection_id, last_modified DESC);
CREATE INDEX IF NOT EXISTS idx_records_last_modified_epoch
    ON records(as_epoch(last_modified));


CREATE TABLE IF NOT EXISTS timestamps (
  parent_id TEXT NOT NULL,
  collection_id TEXT NOT NULL,
  last_modified TIMESTAMP NOT NULL,
  PRIMARY KEY (parent_id, collection_id)
);

--
-- Triggers to set last_modified on INSERT/UPDATE
--
DROP TRIGGER IF EXISTS tgr_records_last_modified ON records;

CREATE OR REPLACE FUNCTION bump_timestamp()
RETURNS trigger AS $$
DECLARE
    previous TIMESTAMP;
    current TIMESTAMP;
BEGIN
    previous := NULL;
    WITH existing_timestamps AS (
      -- Timestamp of latest record.
      (
        SELECT last_modified
        FROM records
        WHERE parent_id = NEW.parent_id
          AND collection_id = NEW.collection_id
        ORDER BY last_modified DESC
        LIMIT 1
      )
      -- Timestamp when collection was empty.
      UNION
      (
        SELECT last_modified
        FROM timestamps
        WHERE parent_id = NEW.parent_id
          AND collection_id = NEW.collection_id
      )
    )
    SELECT MAX(last_modified) INTO previous
      FROM existing_timestamps;

    --
    -- This bumps the current timestamp to 1 msec in the future if the previous
    -- timestamp is equal to the current one (or higher if was bumped already).
    --
    -- If a bunch of requests from the same user on the same collection
    -- arrive in the same millisecond, the unicity constraint can raise
    -- an error (operation is cancelled).
    -- See https://github.com/mozilla-services/cliquet/issues/25
    --
    current := clock_timestamp();
    IF previous IS NOT NULL AND previous >= current THEN
        current := previous + INTERVAL '1 milliseconds';
    END IF;

    IF NEW.last_modified IS NULL OR
       (previous IS NOT NULL AND as_epoch(NEW.last_modified) = as_epoch(previous)) THEN
        -- If record does not carry last-modified, or if the one specified
        -- is equal to previous, assign it to current (i.e. bump it).
        NEW.last_modified := current;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_records_last_modified
BEFORE INSERT OR UPDATE OF data ON records
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
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '19');
