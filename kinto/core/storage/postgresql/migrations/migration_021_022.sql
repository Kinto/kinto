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

    --
    -- This bumps the current timestamp to 1 msec in the future if the previous
    -- timestamp is equal to the current one (or higher if was bumped already).
    --
    -- If a bunch of requests from the same user on the same resource
    -- arrive in the same millisecond, the unicity constraint can raise
    -- an error (operation is cancelled).
    -- See https://github.com/mozilla-services/cliquet/issues/25
    --
    current := as_epoch(clock_timestamp()::TIMESTAMP);
    IF previous IS NOT NULL AND previous >= current THEN
        current := previous + 1;
    END IF;

    IF NEW.last_modified IS NULL OR
       (previous IS NOT NULL AND as_epoch(NEW.last_modified) = previous) THEN
        -- If record does not carry last-modified, or if the one specified
        -- is equal to previous, assign it to current (i.e. bump it).
        NEW.last_modified := from_epoch(current);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_objects_last_modified
BEFORE INSERT OR UPDATE OF data ON objects
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '22');
