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
