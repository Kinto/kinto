CREATE OR REPLACE FUNCTION as_epoch(ts TIMESTAMP) RETURNS BIGINT AS $$
BEGIN
    RETURN (EXTRACT(EPOCH FROM (ts AT TIME ZONE current_setting('TIMEZONE'))) * 1000)::BIGINT;
END;
$$ LANGUAGE plpgsql
IMMUTABLE;

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '23');
