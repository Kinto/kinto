CREATE TABLE IF NOT EXISTS timestamps (
  parent_id TEXT NOT NULL,
  collection_id TEXT NOT NULL,
  last_modified TIMESTAMP NOT NULL,
  PRIMARY KEY (parent_id, collection_id)
);


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

DROP TRIGGER IF EXISTS tgr_records_last_modified ON records;
DROP TRIGGER IF EXISTS tgr_deleted_last_modified ON deleted;

CREATE OR REPLACE FUNCTION bump_timestamp()
RETURNS trigger AS $$
DECLARE
    previous TIMESTAMP;
    current TIMESTAMP;

BEGIN
    previous := NULL;
    SELECT last_modified INTO previous
      FROM timestamps
     WHERE parent_id = NEW.parent_id
       AND collection_id = NEW.collection_id;

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


    IF NEW.last_modified IS NULL THEN
        -- If record does not carry last-modified, assign it to current.
        NEW.last_modified := current;
    ELSE
        -- Use record last-modified as collection timestamp.
        IF previous IS NULL OR NEW.last_modified > previous THEN
            current := NEW.last_modified;
        END IF;
    END IF;

    --
    -- Upsert current collection timestamp.
    --
    WITH upsert AS (
        UPDATE timestamps SET last_modified = current
         WHERE parent_id = NEW.parent_id AND collection_id = NEW.collection_id
        RETURNING *
    )
    INSERT INTO timestamps (parent_id, collection_id, last_modified)
    SELECT NEW.parent_id, NEW.collection_id, current
    WHERE NOT EXISTS (SELECT * FROM upsert);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tgr_records_last_modified
BEFORE INSERT OR UPDATE ON records
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

CREATE TRIGGER tgr_deleted_last_modified
BEFORE INSERT OR UPDATE ON deleted
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();


-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '10');
