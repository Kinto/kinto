CREATE TABLE IF NOT EXISTS cache (
    key VARCHAR(256) PRIMARY KEY,
    value TEXT NOT NULL,
    ttl TIMESTAMP DEFAULT NULL
);
DROP INDEX IF EXISTS idx_cache_ttl;
CREATE INDEX idx_cache_ttl ON cache(ttl);

CREATE OR REPLACE FUNCTION sec2ttl(seconds FLOAT)
RETURNS TIMESTAMP AS $$
BEGIN
    IF seconds IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN now() + (seconds || ' SECOND')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
