-- Alter collation to C to improve LIKE-prefix queries in delete_all.
ALTER TABLE timestamps
    ALTER COLUMN parent_id TYPE TEXT COLLATE "C",
    ALTER COLUMN collection_id TYPE TEXT COLLATE "C";

-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '20');
