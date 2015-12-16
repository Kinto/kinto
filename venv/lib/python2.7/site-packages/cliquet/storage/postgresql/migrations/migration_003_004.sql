ALTER TABLE records
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id SET DATA TYPE TEXT,
    ALTER COLUMN user_id SET DATA TYPE TEXT,
    ALTER COLUMN resource_name SET DATA TYPE TEXT;

ALTER TABLE deleted
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id SET DATA TYPE TEXT,
    ALTER COLUMN user_id SET DATA TYPE TEXT,
    ALTER COLUMN resource_name SET DATA TYPE TEXT;


DROP EXTENSION IF EXISTS "uuid-ossp";


-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '4');
