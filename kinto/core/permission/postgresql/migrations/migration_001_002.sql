-- Same table as exists in the storage backend, but used to track
-- migration status for both. Only one schema actually has to create
-- it.
CREATE TABLE IF NOT EXISTS metadata (
    name VARCHAR(128) NOT NULL,
    value VARCHAR(512) NOT NULL
);

ALTER TABLE user_principals
    ALTER COLUMN user_id TYPE TEXT COLLATE "C";

ALTER TABLE access_control_entries
    ALTER COLUMN object_id TYPE TEXT COLLATE "C";

INSERT INTO metadata VALUES ('permission_schema_version', '2');
