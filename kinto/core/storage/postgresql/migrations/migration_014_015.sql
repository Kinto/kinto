--
-- Find timestamp in case of conflict
--

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

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '15');
