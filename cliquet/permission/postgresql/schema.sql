--
-- Automated script, we do not need NOTICE and WARNING
--
SET client_min_messages TO ERROR;

CREATE TABLE IF NOT EXISTS user_principals (
    user_id TEXT,
    principal TEXT,

    PRIMARY KEY (user_id, principal)
);

CREATE TABLE IF NOT EXISTS access_control_entries (
    object_id TEXT,
    permission TEXT,
    principal TEXT,

    PRIMARY KEY (object_id, permission, principal)
);

--
-- CREATE INDEX IF NOT EXISTS will be available in PostgreSQL 9.5
-- http://www.postgresql.org/docs/9.5/static/sql-createindex.html
DO $$
BEGIN

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
       WHERE indexname = 'idx_access_control_entries_object_id'
       AND tablename = 'access_control_entries'
  ) THEN
  CREATE INDEX idx_access_control_entries_object_id
    ON access_control_entries(object_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
       WHERE indexname = 'idx_access_control_entries_permission'
       AND tablename = 'access_control_entries'
  ) THEN
  CREATE INDEX idx_access_control_entries_permission
    ON access_control_entries(permission);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
       WHERE indexname = 'idx_access_control_entries_principal'
       AND tablename = 'access_control_entries'
  ) THEN
  CREATE INDEX idx_access_control_entries_principal
    ON access_control_entries(principal);
  END IF;

END$$;
