DROP TRIGGER IF EXISTS tgr_records_last_modified ON records;
DROP TRIGGER IF EXISTS tgr_deleted_last_modified ON deleted;

CREATE TRIGGER tgr_records_last_modified
BEFORE INSERT OR UPDATE OF data ON records
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();

CREATE TRIGGER tgr_deleted_last_modified
BEFORE INSERT ON deleted
FOR EACH ROW EXECUTE PROCEDURE bump_timestamp();


-- Bump storage schema version.
INSERT INTO metadata (name, value) VALUES ('storage_schema_version', '14');
