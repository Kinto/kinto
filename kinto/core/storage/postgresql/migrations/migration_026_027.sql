-- Update bump_timestamp trigger to operate directly on PostgreSQL TIMESTAMP,
-- preserving index-friendly timestamps and bumping safely on concurrent writes.

DROP TRIGGER IF EXISTS tgr_objects_last_modified ON objects;

CREATE OR REPLACE FUNCTION bump_timestamp()
RETURNS trigger AS $$
DECLARE
    previous TIMESTAMP;
    current_ts TIMESTAMP;
BEGIN
    previous := NULL;
    WITH existing_timestamps AS (
      -- Timestamp of latest record.
      (
        SELECT last_modified
        FROM objects
        WHERE parent_id = NEW.parent_id
          AND resource_name = NEW.resource_name
        ORDER BY last_modified DESC
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
    SELECT MAX(last_modified) INTO previous
      FROM existing_timestamps;

    --
    -- This bumps the current timestamp to 1 msec in the future if the previous
    -- timestamp is equal to the current one (or higher if was bumped already).
    --
    current_ts := from_epoch(as_epoch(clock_timestamp()::TIMESTAMP));
    IF previous IS NOT NULL AND previous >= current_ts THEN
        current_ts := previous + INTERVAL '1 millisecond';
    END IF;

    IF NEW.last_modified IS NULL OR
       (previous IS NOT NULL AND as_epoch(NEW.last_modified) = as_epoch(previous)) THEN
        -- If record does not carry last-modified, or if the one specified
        -- is equal to previous, assign it to current (i.e. bump it).
        NEW.last_modified := current_ts;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_objects_last_modified
BEFORE INSERT OR UPDATE OF data ON objects
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '27');
