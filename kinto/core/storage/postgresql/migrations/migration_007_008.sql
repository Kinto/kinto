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
    RETURN coalesce(greatest(ts_deleted, ts_records), clock_timestamp());
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
    current := clock_timestamp();

    IF previous >= current THEN
        current := previous + INTERVAL '1 milliseconds';
    END IF;

    NEW.last_modified := current;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '8');
