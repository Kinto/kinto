import logging
import os
import warnings
from collections import defaultdict

from kinto.core.storage import (
    StorageBase,
    exceptions,
    DEFAULT_ID_FIELD,
    DEFAULT_MODIFIED_FIELD,
    DEFAULT_DELETED_FIELD,
    MISSING,
)
from kinto.core.decorators import deprecate_kwargs
from kinto.core.storage.postgresql.client import create_from_config
from kinto.core.storage.postgresql.migrator import MigratorMixin
from kinto.core.utils import COMPARISON


logger = logging.getLogger(__name__)
HERE = os.path.dirname(__file__)


class Storage(StorageBase, MigratorMixin):
    """Storage backend using PostgreSQL.

    Recommended in production (*requires PostgreSQL 9.4 or higher*).

    Enable in configuration::

        kinto.storage_backend = kinto.core.storage.postgresql

    Database location URI can be customized::

        kinto.storage_url = postgresql://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in :file:`~/.pgpass` (*see PostgreSQL documentation*).

    .. note::

        Some tables and indices are created when ``kinto migrate`` is run.
        This requires some privileges on the database, or some error will
        be raised.

        **Alternatively**, the schema can be initialized outside the
        python application, using the SQL file located in
        :file:`kinto/core/storage/postgresql/schema.sql`. This allows to
        distinguish schema manipulation privileges from schema usage.


    A connection pool is enabled by default::

        kinto.storage_pool_size = 10
        kinto.storage_maxoverflow = 10
        kinto.storage_max_backlog = -1
        kinto.storage_pool_recycle = -1
        kinto.storage_pool_timeout = 30
        kinto.cache_poolclass =
            kinto.core.storage.postgresql.pool.QueuePoolWithMaxBacklog

    The ``max_backlog``  limits the number of threads that can be in the queue
    waiting for a connection.  Once this limit has been reached, any further
    attempts to acquire a connection will be rejected immediately, instead of
    locking up all threads by keeping them waiting in the queue.

    See `dedicated section in SQLAlchemy documentation
    <http://docs.sqlalchemy.org/en/rel_1_0/core/engines.html>`_
    for default values and behaviour.

    .. note::

        Using a `dedicated connection pool <http://pgpool.net>`_ is still
        recommended to allow load balancing, replication or limit the number
        of connections used in a multi-process deployment.

    """  # NOQA

    # MigratorMixin attributes.
    name = "storage"
    schema_version = 21
    schema_file = os.path.join(HERE, "schema.sql")
    migrations_directory = os.path.join(HERE, "migrations")

    def __init__(self, client, max_fetch_size, *args, readonly=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self._max_fetch_size = max_fetch_size
        self.readonly = readonly

    def create_schema(self, dry_run=False):
        """Override create_schema to ensure DB encoding and TZ are OK.
        """
        self._check_database_encoding()
        self._check_database_timezone()
        return super().create_schema(dry_run)

    def initialize_schema(self, dry_run=False):
        return self.create_or_migrate_schema(dry_run)

    def _check_database_timezone(self):
        # Make sure database has UTC timezone.
        query = "SELECT current_setting('TIMEZONE') AS timezone;"
        with self.client.connect() as conn:
            result = conn.execute(query)
            obj = result.fetchone()
        timezone = obj["timezone"].upper()
        if timezone != "UTC":  # pragma: no cover
            msg = f"Database timezone is not UTC ({timezone})"
            warnings.warn(msg)
            logger.warning(msg)

    def _check_database_encoding(self):
        # Make sure database is UTF-8.
        query = """
        SELECT pg_encoding_to_char(encoding) AS encoding
          FROM pg_database
         WHERE datname =  current_database();
        """
        with self.client.connect() as conn:
            result = conn.execute(query)
            obj = result.fetchone()
        encoding = obj["encoding"].lower()
        if encoding != "utf8":  # pragma: no cover
            raise AssertionError(f"Unexpected database encoding {encoding}")

    def get_installed_version(self):
        """Return current version of schema or None if not any found.
        """
        # Check for objects table, which definitely indicates a new
        # DB. (metadata can exist if the permission schema ran first.)
        table_exists_query = """
        SELECT table_name
          FROM information_schema.tables
         WHERE table_name = '{}';
        """
        schema_version_metadata_query = """
        SELECT value AS version
          FROM metadata
         WHERE name = 'storage_schema_version'
         ORDER BY LPAD(value, 3, '0') DESC;
        """
        with self.client.connect() as conn:
            result = conn.execute(table_exists_query.format("objects"))
            objects_table_exists = result.rowcount > 0
            result = conn.execute(table_exists_query.format("records"))
            records_table_exists = result.rowcount > 0

            if not objects_table_exists and not records_table_exists:
                return

            result = conn.execute(schema_version_metadata_query)
            if result.rowcount > 0:
                return int(result.fetchone()["version"])

            # No storage_schema_version row.
            # Perhaps it got flush()ed by a pre-8.1.2 Kinto (which
            # would wipe the metadata table).
            # Alternately, maybe we are working from a very early
            # Cliquet version which never had a migration.
            # Check for a created_at row. If this is gone, it's
            # probably been flushed at some point.
            query = "SELECT COUNT(*) FROM metadata WHERE name = 'created_at';"
            result = conn.execute(query)
            was_flushed = int(result.fetchone()[0]) == 0
            if not was_flushed:
                error_msg = "No schema history; assuming migration from Cliquet (version 1)."
                logger.warning(error_msg)
                return 1

            # We have no idea what the schema is here. Migration
            # is completely broken.
            # Log an obsequious error message to the user and try
            # to recover by assuming the last version where we had
            # this bug.
            logger.warning(UNKNOWN_SCHEMA_VERSION_MESSAGE)

            # This is the last schema version where flushing the
            # server would delete the schema version.
            MAX_FLUSHABLE_SCHEMA_VERSION = 20
            return MAX_FLUSHABLE_SCHEMA_VERSION

    def flush(self, auth=None):
        """Delete objects from tables without destroying schema.

        This is used in test suites as well as in the flush plugin.
        """
        query = """
        DELETE FROM objects;
        DELETE FROM timestamps;
        """
        with self.client.connect(force_commit=True) as conn:
            conn.execute(query)
        logger.debug("Flushed PostgreSQL storage tables")

    def resource_timestamp(self, resource_name, parent_id, auth=None):
        query_existing = """
        WITH existing_timestamps AS (
          -- Timestamp of latest object.
          (
            SELECT last_modified, as_epoch(last_modified) AS last_epoch
            FROM objects
            WHERE parent_id = :parent_id
              AND resource_name = :resource_name
            ORDER BY last_modified DESC
            LIMIT 1
          )
          -- Timestamp of empty resource.
          UNION
          (
            SELECT last_modified, as_epoch(last_modified) AS last_epoch
            FROM timestamps
            WHERE parent_id = :parent_id
              AND resource_name = :resource_name
          )
        )
        SELECT MAX(last_modified) AS last_modified, MAX(last_epoch) AS last_epoch
          FROM existing_timestamps
        """

        create_if_missing = """
        INSERT INTO timestamps (parent_id, resource_name, last_modified)
        VALUES (:parent_id, :resource_name, COALESCE(:last_modified, clock_timestamp()::timestamp))
        ON CONFLICT (parent_id, resource_name) DO NOTHING
        RETURNING as_epoch(last_modified) AS last_epoch
        """

        placeholders = dict(parent_id=parent_id, resource_name=resource_name)
        with self.client.connect(readonly=False) as conn:
            existing_ts = None
            ts_result = conn.execute(query_existing, placeholders)
            row = ts_result.fetchone()  # Will return (None, None) when empty.
            existing_ts = row["last_modified"]

            # If the backend is readonly, we should not try to create the timestamp.
            if self.readonly:
                if existing_ts is None:
                    error_msg = (
                        "Cannot initialize empty resource timestamp " "when running in readonly."
                    )
                    raise exceptions.BackendError(message=error_msg)
                obj = row
            else:
                create_result = conn.execute(
                    create_if_missing, dict(last_modified=existing_ts, **placeholders)
                )
                obj = create_result.fetchone() or row

        return obj["last_epoch"]

    @deprecate_kwargs({"collection_id": "resource_name", "record": "obj"})
    def create(
        self,
        resource_name,
        parent_id,
        obj,
        id_generator=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        id_generator = id_generator or self.id_generator
        obj = {**obj}
        if id_field in obj:
            # Optimistically raise unicity error if object with same
            # id already exists.
            # Even if this check doesn't find one, be robust against
            # conflicts because we could race with another thread.
            # Still, this reduces write load because SELECTs are
            # cheaper than INSERTs.
            try:
                existing = self.get(resource_name, parent_id, obj[id_field])
                raise exceptions.UnicityError(id_field, existing)
            except exceptions.ObjectNotFoundError:
                pass
        else:
            obj[id_field] = id_generator()

        # Remove redundancy in data field
        query_object = {**obj}
        query_object.pop(id_field, None)
        query_object.pop(modified_field, None)

        # If there is an object in the table and it is deleted = TRUE,
        # we want to replace it. Otherwise, we want to do nothing and
        # throw a UnicityError. Per
        # https://stackoverflow.com/questions/15939902/is-select-or-insert-in-a-function-prone-to-race-conditions/15950324#15950324
        # a WHERE clause in the DO UPDATE will lock the conflicting
        # row whether it is true or not, so the subsequent SELECT is
        # safe. We add a constant "inserted" field to know whether we
        # need to throw or not.
        query = """
        INSERT INTO objects (id, parent_id, resource_name, data, last_modified, deleted)
        VALUES (:object_id, :parent_id,
                :resource_name, (:data)::JSONB,
                from_epoch(:last_modified),
                FALSE)
        ON CONFLICT (id, parent_id, resource_name) DO UPDATE
        SET last_modified = from_epoch(:last_modified),
            data = (:data)::JSONB,
            deleted = FALSE
        WHERE objects.deleted = TRUE
        RETURNING id, data, as_epoch(last_modified) AS last_modified;
        """

        safe_holders = {}
        placeholders = dict(
            object_id=obj[id_field],
            parent_id=parent_id,
            resource_name=resource_name,
            last_modified=obj.get(modified_field),
            data=self.json.dumps(query_object),
        )
        with self.client.connect() as conn:
            result = conn.execute(query % safe_holders, placeholders)
            inserted = result.fetchone()

        if not inserted:
            raise exceptions.UnicityError(id_field)

        obj[modified_field] = inserted["last_modified"]
        return obj

    @deprecate_kwargs({"collection_id": "resource_name"})
    def get(
        self,
        resource_name,
        parent_id,
        object_id,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        query = """
        SELECT as_epoch(last_modified) AS last_modified, data
          FROM objects
         WHERE id = :object_id
           AND parent_id = :parent_id
           AND resource_name = :resource_name
           AND NOT deleted;
        """
        placeholders = dict(object_id=object_id, parent_id=parent_id, resource_name=resource_name)
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            if result.rowcount == 0:
                raise exceptions.ObjectNotFoundError(object_id)
            else:
                existing = result.fetchone()

        obj = existing["data"]
        obj[id_field] = object_id
        obj[modified_field] = existing["last_modified"]
        return obj

    @deprecate_kwargs({"collection_id": "resource_name", "record": "obj"})
    def update(
        self,
        resource_name,
        parent_id,
        object_id,
        obj,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):

        # Remove redundancy in data field
        query_object = {**obj}
        query_object.pop(id_field, None)
        query_object.pop(modified_field, None)

        query = """
        INSERT INTO objects (id, parent_id, resource_name, data, last_modified, deleted)
        VALUES (:object_id, :parent_id,
                :resource_name, (:data)::JSONB,
                from_epoch(:last_modified),
                FALSE)
        ON CONFLICT (id, parent_id, resource_name) DO UPDATE
        SET data = (:data)::JSONB,
            deleted = FALSE,
            last_modified = GREATEST(from_epoch(:last_modified),
                                     EXCLUDED.last_modified)
        RETURNING as_epoch(last_modified) AS last_modified;
        """
        placeholders = dict(
            object_id=object_id,
            parent_id=parent_id,
            resource_name=resource_name,
            last_modified=obj.get(modified_field),
            data=self.json.dumps(query_object),
        )

        with self.client.connect() as conn:
            result = conn.execute(query, placeholders)
            updated = result.fetchone()

        obj = {**obj, id_field: object_id}
        obj[modified_field] = updated["last_modified"]
        return obj

    @deprecate_kwargs({"collection_id": "resource_name"})
    def delete(
        self,
        resource_name,
        parent_id,
        object_id,
        id_field=DEFAULT_ID_FIELD,
        with_deleted=True,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
        last_modified=None,
    ):
        if with_deleted:
            query = """
            UPDATE objects
               SET deleted=TRUE,
                   data=(:deleted_data)::JSONB,
                   last_modified=from_epoch(:last_modified)
             WHERE id = :object_id
               AND parent_id = :parent_id
               AND resource_name = :resource_name
               AND NOT deleted
            RETURNING as_epoch(last_modified) AS last_modified;
            """
        else:
            query = """
            DELETE FROM objects
            WHERE id = :object_id
               AND parent_id = :parent_id
               AND resource_name = :resource_name
               AND NOT deleted
            RETURNING as_epoch(last_modified) AS last_modified;
            """
        deleted_data = self.json.dumps(dict([(deleted_field, True)]))
        placeholders = dict(
            object_id=object_id,
            parent_id=parent_id,
            resource_name=resource_name,
            last_modified=last_modified,
            deleted_data=deleted_data,
        )

        with self.client.connect() as conn:
            result = conn.execute(query, placeholders)
            if result.rowcount == 0:
                raise exceptions.ObjectNotFoundError(object_id)
            updated = result.fetchone()

        obj = {}
        obj[modified_field] = updated["last_modified"]
        obj[id_field] = object_id

        obj[deleted_field] = True
        return obj

    @deprecate_kwargs({"collection_id": "resource_name"})
    def delete_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        id_field=DEFAULT_ID_FIELD,
        with_deleted=True,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):
        if with_deleted:
            query = """
            WITH matching_objects AS (
                SELECT id, parent_id, resource_name
                    FROM objects
                    WHERE {parent_id_filter}
                          {resource_name_filter}
                          AND NOT deleted
                          {conditions_filter}
                          {pagination_rules}
                    {sorting}
                    LIMIT :pagination_limit
                    FOR UPDATE
            )
            UPDATE objects
               SET deleted=TRUE, data=(:deleted_data)::JSONB, last_modified=NULL
              FROM matching_objects
             WHERE objects.id = matching_objects.id
               AND objects.parent_id = matching_objects.parent_id
               AND objects.resource_name = matching_objects.resource_name
            RETURNING objects.id, as_epoch(last_modified) AS last_modified;
            """
        else:
            query = """
            WITH matching_objects AS (
                SELECT id, parent_id, resource_name
                    FROM objects
                    WHERE {parent_id_filter}
                          {resource_name_filter}
                          AND NOT deleted
                          {conditions_filter}
                          {pagination_rules}
                    {sorting}
                    LIMIT :pagination_limit
                    FOR UPDATE
            )
            DELETE
            FROM objects
            USING matching_objects
            WHERE objects.id = matching_objects.id
              AND objects.parent_id = matching_objects.parent_id
              AND objects.resource_name = matching_objects.resource_name
            RETURNING objects.id, as_epoch(last_modified) AS last_modified;
            """

        id_field = id_field or self.id_field
        modified_field = modified_field or self.modified_field
        deleted_data = self.json.dumps(dict([(deleted_field, True)]))
        placeholders = dict(
            parent_id=parent_id, resource_name=resource_name, deleted_data=deleted_data
        )
        # Safe strings
        safeholders = defaultdict(str)
        # Handle parent_id as a regex only if it contains *
        if "*" in parent_id:
            safeholders["parent_id_filter"] = "parent_id LIKE :parent_id"
            placeholders["parent_id"] = parent_id.replace("*", "%")
        else:
            safeholders["parent_id_filter"] = "parent_id = :parent_id"
        # If resource is None, remove it from query.
        if resource_name is None:
            safeholders["resource_name_filter"] = ""
        else:
            safeholders["resource_name_filter"] = "AND resource_name = :resource_name"  # NOQA

        if filters:
            safe_sql, holders = self._format_conditions(filters, id_field, modified_field)
            safeholders["conditions_filter"] = f"AND {safe_sql}"
            placeholders.update(**holders)

        if sorting:
            sql, holders = self._format_sorting(sorting, id_field, modified_field)
            safeholders["sorting"] = sql
            placeholders.update(**holders)

        if pagination_rules:
            sql, holders = self._format_pagination(pagination_rules, id_field, modified_field)
            safeholders["pagination_rules"] = f"AND ({sql})"
            placeholders.update(**holders)

        # Limit the number of results (pagination).
        limit = min(self._max_fetch_size, limit) if limit else self._max_fetch_size
        placeholders["pagination_limit"] = limit

        with self.client.connect() as conn:
            result = conn.execute(query.format_map(safeholders), placeholders)
            deleted = result.fetchmany(self._max_fetch_size)

        objects = []
        for result in deleted:
            obj = {}
            obj[id_field] = result["id"]
            obj[modified_field] = result["last_modified"]
            obj[deleted_field] = True
            objects.append(obj)

        return objects

    @deprecate_kwargs({"collection_id": "resource_name"})
    def purge_deleted(
        self,
        resource_name,
        parent_id,
        before=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        auth=None,
    ):
        delete_tombstones = """
        DELETE
        FROM objects
        WHERE {parent_id_filter}
              {resource_name_filter}
              {conditions_filter}
        """
        id_field = id_field or self.id_field
        modified_field = modified_field or self.modified_field
        placeholders = dict(parent_id=parent_id, resource_name=resource_name)
        # Safe strings
        safeholders = defaultdict(str)
        # Handle parent_id as a regex only if it contains *
        if "*" in parent_id:
            safeholders["parent_id_filter"] = "parent_id LIKE :parent_id"
            placeholders["parent_id"] = parent_id.replace("*", "%")
        else:
            safeholders["parent_id_filter"] = "parent_id = :parent_id"
        # If resource is None, remove it from query.
        if resource_name is None:
            safeholders["resource_name_filter"] = ""
        else:
            safeholders["resource_name_filter"] = "AND resource_name = :resource_name"  # NOQA

        if before is not None:
            safeholders["conditions_filter"] = "AND as_epoch(last_modified) < :before"
            placeholders["before"] = before

        with self.client.connect() as conn:
            result = conn.execute(delete_tombstones.format_map(safeholders), placeholders)
            deleted = result.rowcount

            # If purging everything from a parent_id, then clear timestamps.
            if resource_name is None and before is None:
                delete_timestamps = """
                DELETE
                FROM timestamps
                WHERE {parent_id_filter}
                """
                conn.execute(delete_timestamps.format_map(safeholders), placeholders)

        return deleted

    def list_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):

        query = """
            SELECT id, as_epoch(last_modified) AS last_modified, data
            FROM objects
            WHERE {parent_id_filter}
            AND resource_name = :resource_name
            {conditions_deleted}
            {conditions_filter}
            {pagination_rules}
            {sorting}
            LIMIT :pagination_limit;
        """

        rows = self._get_rows(
            query,
            resource_name,
            parent_id,
            filters=filters,
            sorting=sorting,
            pagination_rules=pagination_rules,
            limit=limit,
            include_deleted=include_deleted,
            id_field=id_field,
            modified_field=modified_field,
            deleted_field=deleted_field,
            auth=auth,
        )

        if len(rows) == 0:
            return []

        records = []
        for result in rows:
            record = result["data"]
            record[id_field] = result["id"]
            record[modified_field] = result["last_modified"]
            records.append(record)
        return records

    def count_all(
        self,
        resource_name,
        parent_id,
        filters=None,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):

        query = """
            SELECT COUNT(*) AS total_count
            FROM objects
            WHERE {parent_id_filter}
            AND resource_name = :resource_name
            AND NOT deleted
            {conditions_filter}
        """
        rows = self._get_rows(
            query,
            resource_name,
            parent_id,
            filters=filters,
            id_field=id_field,
            modified_field=modified_field,
            deleted_field=deleted_field,
            auth=auth,
        )
        return rows[0]["total_count"]

    def _get_rows(
        self,
        query,
        resource_name,
        parent_id,
        filters=None,
        sorting=None,
        pagination_rules=None,
        limit=None,
        include_deleted=False,
        id_field=DEFAULT_ID_FIELD,
        modified_field=DEFAULT_MODIFIED_FIELD,
        deleted_field=DEFAULT_DELETED_FIELD,
        auth=None,
    ):

        # Unsafe strings escaped by PostgreSQL
        placeholders = dict(parent_id=parent_id, resource_name=resource_name)

        # Safe strings
        safeholders = defaultdict(str)

        # Handle parent_id as a regex only if it contains *
        if "*" in parent_id:
            safeholders["parent_id_filter"] = "parent_id LIKE :parent_id"
            placeholders["parent_id"] = parent_id.replace("*", "%")
        else:
            safeholders["parent_id_filter"] = "parent_id = :parent_id"

        if filters:
            safe_sql, holders = self._format_conditions(filters, id_field, modified_field)
            safeholders["conditions_filter"] = f"AND {safe_sql}"
            placeholders.update(**holders)

        if not include_deleted:
            safeholders["conditions_deleted"] = "AND NOT deleted"

        if sorting:
            sql, holders = self._format_sorting(sorting, id_field, modified_field)
            safeholders["sorting"] = sql
            placeholders.update(**holders)

        if pagination_rules:
            sql, holders = self._format_pagination(pagination_rules, id_field, modified_field)
            safeholders["pagination_rules"] = f"AND ({sql})"
            placeholders.update(**holders)

        # Limit the number of results (pagination).
        limit = min(self._max_fetch_size + 1, limit) if limit else self._max_fetch_size
        placeholders["pagination_limit"] = limit

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query.format_map(safeholders), placeholders)
            return result.fetchmany(self._max_fetch_size + 1)

    def _format_conditions(self, filters, id_field, modified_field, prefix="filters"):
        """Format the filters list in SQL, with placeholders for safe escaping.

        .. note::
            All conditions are combined using AND.

        .. note::

            Field name and value are escaped as they come from HTTP API.

        :returns: A SQL string with placeholders, and a dict mapping
            placeholders to actual values.
        :rtype: tuple
        """
        operators = {
            COMPARISON.EQ: "=",
            COMPARISON.NOT: "<>",
            COMPARISON.IN: "IN",
            COMPARISON.EXCLUDE: "NOT IN",
            COMPARISON.LIKE: "ILIKE",
            COMPARISON.CONTAINS: "@>",
        }

        conditions = []
        holders = {}
        for i, filtr in enumerate(filters):
            value = filtr.value
            is_like_query = filtr.operator == COMPARISON.LIKE

            if filtr.field == id_field:
                sql_field = "id"
                if isinstance(value, int):
                    value = str(value)
            elif filtr.field == modified_field:
                sql_field = "as_epoch(last_modified)"
            else:
                column_name = "data"
                # Subfields: ``person.name`` becomes ``data->person->>name``
                subfields = filtr.field.split(".")
                for j, subfield in enumerate(subfields):
                    # Safely escape field name
                    field_holder = f"{prefix}_field_{i}_{j}"
                    holders[field_holder] = subfield
                    # Use ->> to convert the last level to text if
                    # needed for LIKE query. (Other queries do JSONB comparison.)
                    column_name += "->>" if j == len(subfields) - 1 and is_like_query else "->"
                    column_name += f":{field_holder}"
                sql_field = column_name

            string_field = filtr.field in (id_field, modified_field) or is_like_query
            if not string_field and value != MISSING:
                # JSONB-ify the value.
                if filtr.operator not in (
                    COMPARISON.IN,
                    COMPARISON.EXCLUDE,
                    COMPARISON.CONTAINS_ANY,
                ):
                    value = self.json.dumps(value)
                else:
                    value = [self.json.dumps(v) for v in value]

            if filtr.operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                value = tuple(value)
                # WHERE field IN ();  -- Fails with syntax error.
                if len(value) == 0:
                    value = (None,)

            if is_like_query:
                # Operand should be a string.
                # Add implicit start/end wildcards if none is specified.
                if "*" not in value:
                    value = f"*{value}*"
                value = value.replace("*", "%")

            if filtr.operator == COMPARISON.HAS:
                operator = "IS NOT NULL" if filtr.value else "IS NULL"
                cond = f"{sql_field} {operator}"

            elif filtr.operator == COMPARISON.CONTAINS_ANY:
                value_holder = f"{prefix}_value_{i}"
                holders[value_holder] = value
                # In case the field is not a sequence, we ignore the object.
                is_json_sequence = f"jsonb_typeof({sql_field}) = 'array'"
                # Postgres's && operator doesn't support jsonbs.
                # However, it does support Postgres arrays of any
                # type. Assume that the referenced field is a JSON
                # array and convert it to a Postgres array.
                data_as_array = f"""
                (SELECT array_agg(elems) FROM jsonb_array_elements({sql_field}) elems)
                """
                cond = f"{is_json_sequence} AND {data_as_array} && (:{value_holder})::jsonb[]"

            elif value != MISSING:
                # Safely escape value. MISSINGs get handled below.
                value_holder = f"{prefix}_value_{i}"
                holders[value_holder] = value

                sql_operator = operators.setdefault(filtr.operator, filtr.operator.value)
                cond = f"{sql_field} {sql_operator} :{value_holder}"

            # If the field is missing, column_name will produce
            # NULL. NULL has strange properties with comparisons
            # in SQL -- NULL = anything => NULL, NULL <> anything => NULL.
            # We generally want missing fields to be treated as a
            # special value that compares as different from
            # everything, including JSON null. Do this on a
            # per-operator basis.
            null_false_operators = (
                # NULLs aren't EQ to anything (definitionally).
                COMPARISON.EQ,
                # So they can't match anything in an INCLUDE.
                COMPARISON.IN,
                # Nor can they be LIKE anything.
                COMPARISON.LIKE,
                # NULLs don't contain anything.
                COMPARISON.CONTAINS,
                COMPARISON.CONTAINS_ANY,
            )
            null_true_operators = (
                # NULLs are automatically not equal to everything.
                COMPARISON.NOT,
                # Thus they can never be excluded.
                COMPARISON.EXCLUDE,
                # Match Postgres's default sort behavior
                # (NULLS LAST) by allowing NULLs to
                # automatically be greater than everything.
                COMPARISON.GT,
                COMPARISON.MIN,
            )

            if not (filtr.field == id_field or filtr.field == modified_field):
                if value == MISSING:
                    # Handle MISSING values. The main use case for this is
                    # pagination, since there's no way to encode MISSING
                    # at the HTTP API level. Because we only need to cover
                    # pagination, we don't have to worry about any
                    # operators besides LT, LE, GT, GE, and EQ, and
                    # never worry about id_field or modified_field.
                    #
                    # Comparing a value against NULL is not the same
                    # as comparing a NULL against some other value, so
                    # we need another set of operators for which
                    # NULLs are OK.
                    if filtr.operator in (COMPARISON.EQ, COMPARISON.MIN):
                        # If a row is NULL, then it can be == NULL
                        # (for the purposes of pagination).
                        # >= NULL should only match rows that are
                        # NULL, since there's nothing higher.
                        cond = f"{sql_field} IS NULL"
                    elif filtr.operator == COMPARISON.LT:
                        # If we're looking for < NULL, match only
                        # non-nulls.
                        cond = f"{sql_field} IS NOT NULL"
                    elif filtr.operator == COMPARISON.MAX:
                        # <= NULL should include everything -- NULL
                        # because it's equal, and non-nulls because
                        # they're <.
                        cond = "TRUE"
                    elif filtr.operator == COMPARISON.GT:
                        # Nothing can be greater than NULL (that is,
                        # higher in search order).
                        cond = "FALSE"
                    else:
                        raise ValueError("Somehow we got a filter with MISSING value")
                elif filtr.operator in null_false_operators:
                    cond = f"({sql_field} IS NOT NULL AND {cond})"
                elif filtr.operator in null_true_operators:
                    cond = f"({sql_field} IS NULL OR {cond})"
                else:
                    # No need to check for LT and MAX because NULL < foo
                    # is NULL, which is falsy in SQL.
                    pass

            conditions.append(cond)

        safe_sql = " AND ".join(conditions)
        return safe_sql, holders

    def _format_pagination(self, pagination_rules, id_field, modified_field):
        """Format the pagination rules in SQL, with placeholders for
        safe escaping.

        .. note::

            All rules are combined using OR.

        .. note::

            Field names are escaped as they come from HTTP API.

        :returns: A SQL string with placeholders, and a dict mapping
            placeholders to actual values.
        :rtype: tuple
        """
        rules = []
        placeholders = {}

        for i, rule in enumerate(pagination_rules):
            prefix = f"rules_{i}"
            safe_sql, holders = self._format_conditions(
                rule, id_field, modified_field, prefix=prefix
            )
            rules.append(safe_sql)
            placeholders.update(**holders)

        # Unsure how to convert to fstrings
        safe_sql = " OR ".join([f"({r})" for r in rules])
        return safe_sql, placeholders

    def _format_sorting(self, sorting, id_field, modified_field):
        """Format the sorting in SQL, with placeholders for safe escaping.

        .. note::

            Field names are escaped as they come from HTTP API.

        :returns: A SQL string with placeholders, and a dict mapping
            placeholders to actual values.
        :rtype: tuple
        """
        sorts = []
        holders = {}
        for i, sort in enumerate(sorting):

            if sort.field == id_field:
                sql_field = "id"
            elif sort.field == modified_field:
                sql_field = "last_modified"
            else:
                # Subfields: ``person.name`` becomes ``data->person->name``
                subfields = sort.field.split(".")
                sql_field = "data"
                for j, subfield in enumerate(subfields):
                    # Safely escape field name
                    field_holder = f"sort_field_{i}_{j}"
                    holders[field_holder] = subfield
                    sql_field += f"->(:{field_holder})"

            sql_direction = "ASC" if sort.direction > 0 else "DESC"
            sql_sort = f"{sql_field} {sql_direction}"
            sorts.append(sql_sort)

        safe_sql = f"ORDER BY {', '.join(sorts)}"
        return safe_sql, holders


def load_from_config(config):
    settings = config.get_settings()
    max_fetch_size = int(settings["storage_max_fetch_size"])
    strict = settings.get("storage_strict_json", False)
    readonly = settings.get("readonly", False)
    client = create_from_config(config, prefix="storage_")
    return Storage(
        client=client, max_fetch_size=max_fetch_size, strict_json=strict, readonly=readonly
    )


UNKNOWN_SCHEMA_VERSION_MESSAGE = """
Missing schema history. Perhaps at some point, this Kinto server was
flushed.  Due to a bug in older Kinto versions (see
https://github.com/Kinto/kinto/issues/1460), flushing the server would
cause us to forget what version of the schema was in use. This means
automatic migration is impossible.

Historically, when this happened, Kinto would just assume that the
wiped server had the "current" schema, so you may have been missing a
schema version for quite some time.

To try to recover, we have assumed a schema version corresponding to
the last Kinto version with this bug (schema version 20). However, if
a migration fails, or most queries are broken, you may not actually be
running that schema. You can try to fix this by manually setting the
schema version in the database to what you think it should be using a
command like:

    INSERT INTO metadata VALUES ('storage_schema_version', '19');

See https://github.com/Kinto/kinto/wiki/Schema-versions for more details.

""".strip()
