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

DROP INDEX IF EXISTS idx_access_control_entries_object_id;
CREATE INDEX idx_access_control_entries_object_id ON access_control_entries(object_id);
DROP INDEX IF EXISTS idx_access_control_entries_permission;
CREATE INDEX idx_access_control_entries_permission ON access_control_entries(permission);
DROP INDEX IF EXISTS idx_access_control_entries_principal;
CREATE INDEX idx_access_control_entries_principal ON access_control_entries(principal);
