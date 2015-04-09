ALTER TABLE records
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id SET DATA TYPE VARCHAR(36);

ALTER TABLE deleted
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id SET DATA TYPE VARCHAR(36);


DROP EXTENSION IF EXISTS "uuid-ossp";


-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '4');
