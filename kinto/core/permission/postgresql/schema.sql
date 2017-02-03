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
CREATE INDEX IF NOT EXISTS idx_access_control_entries_object_id
    ON access_control_entries(object_id);
CREATE INDEX IF NOT EXISTS idx_access_control_entries_permission
  ON access_control_entries(permission);
CREATE INDEX IF NOT EXISTS idx_access_control_entries_principal
  ON access_control_entries(principal);
