--
-- Automated script, we do not need NOTICE and WARNING
--
SET client_min_messages TO ERROR;

CREATE TABLE IF NOT EXISTS user_principals (
    user_id TEXT COLLATE "C",
    principal TEXT,

    PRIMARY KEY (user_id, principal)
);

CREATE TABLE IF NOT EXISTS access_control_entries (
    object_id TEXT COLLATE "C",
    permission TEXT,
    principal TEXT,

    PRIMARY KEY (object_id, permission, principal)
);
CREATE INDEX IF NOT EXISTS idx_access_control_entries_object_id
    ON access_control_entries(object_id);
CREATE INDEX IF NOT EXISTS idx_access_control_entries_permission
  ON access_control_entries(permission);
CREATE INDEX IF NOT EXISTS idx_access_control_entries_principal
  ON access_control_entries(principal);

-- Same table as exists in the storage backend, but used to track
-- migration status for both. Only one schema actually has to create
-- it.
CREATE TABLE IF NOT EXISTS metadata (
    name VARCHAR(128) NOT NULL,
    value VARCHAR(512) NOT NULL
);

INSERT INTO metadata VALUES ('permission_schema_version', '2');
