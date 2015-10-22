--
-- Automated script, we do not need NOTICE and WARNING
--
SET client_min_messages TO ERROR;

CREATE TABLE IF NOT EXISTS cache (
    key VARCHAR(256) PRIMARY KEY,
    value TEXT NOT NULL,
    ttl TIMESTAMP DEFAULT NULL
);

--
-- CREATE INDEX IF NOT EXISTS will be available in PostgreSQL 9.5
-- http://www.postgresql.org/docs/9.5/static/sql-createindex.html
DO $$
BEGIN

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
       WHERE indexname = 'idx_cache_ttl'
       AND tablename = 'cache'
  ) THEN

  CREATE INDEX idx_cache_ttl ON cache(ttl);

  END IF;
END$$;


CREATE OR REPLACE FUNCTION sec2ttl(seconds FLOAT)
RETURNS TIMESTAMP AS $$
BEGIN
    IF seconds IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN now() + (seconds || ' SECOND')::INTERVAL;
END;
$$ LANGUAGE plpgsql;
