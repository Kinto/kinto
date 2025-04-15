-- Automated script, we do not need NOTICE and WARNING
SET client_min_messages TO ERROR;

-- Convert timestamps to microseconds epoch integer
CREATE OR REPLACE FUNCTION as_epoch(ts TIMESTAMP) RETURNS NUMERIC AS $$
BEGIN
    RETURN EXTRACT(EPOCH FROM ts) * 1000000;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION from_epoch(epoch BIGINT) RETURNS TIMESTAMP AS $$
BEGIN
    RETURN TIMESTAMP WITH TIME ZONE 'epoch' + epoch * INTERVAL '1 microsecond';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Actual objects
CREATE TABLE IF NOT EXISTS objects (
    id TEXT COLLATE "C" NOT NULL,
    parent_id TEXT COLLATE "C" NOT NULL,
    resource_name TEXT COLLATE "C" NOT NULL,
    last_modified TIMESTAMP NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::JSONB,
    deleted BOOLEAN NOT NULL,
    PRIMARY KEY (id, parent_id, resource_name)
);

-- Update the index to use as_epoch for better precision
CREATE UNIQUE INDEX IF NOT EXISTS idx_objects_parent_id_resource_name_last_modified
    ON objects(parent_id, resource_name, last_modified DESC);
CREATE INDEX IF NOT EXISTS idx_objects_last_modified_epoch_micro
    ON objects(as_epoch(last_modified));

-- Timestamps table
CREATE TABLE IF NOT EXISTS timestamps (
  parent_id TEXT NOT NULL COLLATE "C",
  resource_name TEXT NOT NULL COLLATE "C",
  last_modified TIMESTAMP NOT NULL,
  PRIMARY KEY (parent_id, resource_name)
);

-- Triggers to set last_modified on INSERT/UPDATE
DROP TRIGGER IF EXISTS tgr_objects_last_modified ON objects;

CREATE OR REPLACE FUNCTION bump_timestamp()
RETURNS trigger AS $$
DECLARE
    previous BIGINT;
    current BIGINT;
BEGIN
    previous := NULL;
    WITH existing_timestamps AS (
      -- Timestamp of latest record.
      (
        SELECT last_modified
        FROM objects
        WHERE parent_id = NEW.parent_id
          AND resource_name = NEW.resource_name
        ORDER BY as_epoch(last_modified) DESC
        LIMIT 1
      )
      -- Timestamp when resource was empty.
      UNION
      (
        SELECT last_modified
        FROM timestamps
        WHERE parent_id = NEW.parent_id
          AND resource_name = NEW.resource_name
      )
    )
    SELECT as_epoch(MAX(last_modified)) INTO previous
      FROM existing_timestamps;

    -- This bumps the current timestamp to 1 msec in the future if the previous timestamp is equal to the current one.
    current := as_epoch(clock_timestamp()::TIMESTAMP);
    IF previous IS NOT NULL AND previous >= current THEN
        current := previous + 1;
    END IF;

    IF NEW.last_modified IS NULL OR
       (previous IS NOT NULL AND as_epoch(NEW.last_modified) = previous) THEN
        -- If record does not carry last-modified, or if the one specified is equal to previous, assign it to current (i.e. bump it).
        NEW.last_modified := from_epoch(current);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_objects_last_modified
BEFORE INSERT OR UPDATE OF data ON objects
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    name VARCHAR(128) NOT NULL,
    value VARCHAR(512) NOT NULL
);
INSERT INTO metadata (name, value) VALUES ('created_at', NOW()::TEXT);

-- Set storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '22');
