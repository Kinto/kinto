import logging
import os
import warnings
from collections import defaultdict

from kinto.core.storage import (
    StorageBase, exceptions,
    DEFAULT_ID_FIELD, DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD)
from kinto.core.storage.postgresql.client import create_from_config
from kinto.core.utils import COMPARISON, json


logger = logging.getLogger(__name__)


class Storage(StorageBase):
    """Storage backend using PostgreSQL.

    Recommended in production (*requires PostgreSQL 9.4 or higher*).

    Enable in configuration::

        kinto.storage_backend = kinto.core.storage.postgresql

    Database location URI can be customized::

        kinto.storage_url = postgres://user:pass@db.server.lan:5432/dbname

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

    schema_version = 15

    def __init__(self, client, max_fetch_size, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self._max_fetch_size = max_fetch_size

    def _execute_sql_file(self, filepath):
        with open(filepath) as f:
            schema = f.read()
        # Since called outside request, force commit.
        with self.client.connect(force_commit=True) as conn:
            conn.execute(schema)

    def initialize_schema(self, dry_run=False):
        """Create PostgreSQL tables, and run necessary schema migrations.

        .. note::

            Relies on JSONB fields, available in recent versions of PostgreSQL.
        """
        here = os.path.abspath(os.path.dirname(__file__))

        version = self._get_installed_version()
        if not version:
            filepath = os.path.join(here, 'schema.sql')
            logger.info("Create PostgreSQL storage schema at version "
                        "{} from {}".format(self.schema_version, filepath))
            # Create full schema.
            self._check_database_encoding()
            self._check_database_timezone()
            # Create full schema.
            if not dry_run:
                self._execute_sql_file(filepath)
                logger.info('Created PostgreSQL storage schema (version {}).'.format(
                    self.schema_version))
            return

        logger.info('Detected PostgreSQL storage schema version {}.'.format(version))
        migrations = [(v, v + 1) for v in range(version, self.schema_version)]
        if not migrations:
            logger.info('PostgreSQL storage schema is up-to-date.')
            return

        for migration in migrations:
            # Check order of migrations.
            expected = migration[0]
            current = self._get_installed_version()
            error_msg = "Expected version {}. Found version {}."
            if not dry_run and expected != current:
                raise AssertionError(error_msg.format(expected, current))

            logger.info('Migrate PostgreSQL storage schema from'
                        ' version {} to {}.'.format(*migration))
            filename = 'migration_{0:03d}_{1:03d}.sql'.format(*migration)
            filepath = os.path.join(here, 'migrations', filename)
            logger.info("Execute PostgreSQL storage migration from {}".format(filepath))
            if not dry_run:
                self._execute_sql_file(filepath)
        logger.info("PostgreSQL storage schema migration {}".format(
            "simulated." if dry_run else "done."))

    def _check_database_timezone(self):
        # Make sure database has UTC timezone.
        query = "SELECT current_setting('TIMEZONE') AS timezone;"
        with self.client.connect() as conn:
            result = conn.execute(query)
            record = result.fetchone()
        timezone = record['timezone'].upper()
        if timezone != 'UTC':  # pragma: no cover
            msg = 'Database timezone is not UTC ({})'.format(timezone)
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
            record = result.fetchone()
        encoding = record['encoding'].lower()
        if encoding != 'utf8':  # pragma: no cover
            raise AssertionError('Unexpected database encoding {}'.format(encoding))

    def _get_installed_version(self):
        """Return current version of schema or None if not any found.
        """
        query = "SELECT tablename FROM pg_tables WHERE tablename = 'metadata';"
        with self.client.connect() as conn:
            result = conn.execute(query)
            tables_exist = result.rowcount > 0

        if not tables_exist:
            return

        query = """
        SELECT value AS version
          FROM metadata
         WHERE name = 'storage_schema_version'
         ORDER BY LPAD(value, 3, '0') DESC;
        """
        with self.client.connect() as conn:
            result = conn.execute(query)
            if result.rowcount > 0:
                return int(result.fetchone()['version'])
            else:
                # Guess current version.
                query = "SELECT COUNT(*) FROM metadata;"
                result = conn.execute(query)
                was_flushed = int(result.fetchone()[0]) == 0
                if was_flushed:
                    error_msg = 'Missing schema history: consider version {}.'
                    logger.warning(error_msg.format(self.schema_version))
                    return self.schema_version

                # In the first versions of Cliquet, there was no migration.
                return 1

    def flush(self, auth=None):
        """Delete records from tables without destroying schema. Mainly used
        in tests suites.
        """
        query = """
        DELETE FROM deleted;
        DELETE FROM records;
        DELETE FROM timestamps;
        DELETE FROM metadata;
        """
        with self.client.connect(force_commit=True) as conn:
            conn.execute(query)
        logger.debug('Flushed PostgreSQL storage tables')

    def collection_timestamp(self, collection_id, parent_id, auth=None):
        query = """
        SELECT as_epoch(collection_timestamp(:parent_id, :collection_id))
            AS last_modified;
        """
        placeholders = dict(parent_id=parent_id, collection_id=collection_id)
        with self.client.connect(readonly=False) as conn:
            result = conn.execute(query, placeholders)
            record = result.fetchone()
        return record['last_modified']

    def create(self, collection_id, parent_id, record, id_generator=None,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None, ignore_conflict=False):
        id_generator = id_generator or self.id_generator
        record = {**record}
        if id_field in record:
            # Raise unicity error if record with same id already exists.
            try:
                existing = self.get(collection_id, parent_id, record[id_field])
                if ignore_conflict:
                    return existing
                raise exceptions.UnicityError(id_field, existing)
            except exceptions.RecordNotFoundError:
                pass
        else:
            record[id_field] = id_generator()

        # Remove redundancy in data field
        query_record = {**record}
        query_record.pop(id_field, None)
        query_record.pop(modified_field, None)

        query = """
        WITH delete_potential_tombstone AS (
            DELETE FROM deleted
             WHERE id = :object_id
               AND parent_id = :parent_id
               AND collection_id = :collection_id
        )
        INSERT INTO records (id, parent_id, collection_id, data, last_modified)
        VALUES (:object_id, :parent_id,
                :collection_id, (:data)::JSONB,
                from_epoch(:last_modified))
        %(on_conflict)s
        RETURNING id, as_epoch(last_modified) AS last_modified;
        """

        safe_holders = {"on_conflict": ""}

        if ignore_conflict:
            # We use DO UPDATE so that the RETURNING clause works
            # but we don't update anything and keep the previous
            # last_modified value already stored.
            safe_holders["on_conflict"] = """
            ON CONFLICT (id, parent_id, collection_id) DO UPDATE
            SET last_modified = EXCLUDED.last_modified
            """

        placeholders = dict(object_id=record[id_field],
                            parent_id=parent_id,
                            collection_id=collection_id,
                            last_modified=record.get(modified_field),
                            data=json.dumps(query_record))
        with self.client.connect() as conn:
            result = conn.execute(query % safe_holders, placeholders)
            inserted = result.fetchone()

        record[modified_field] = inserted['last_modified']
        return record

    def get(self, collection_id, parent_id, object_id,
            id_field=DEFAULT_ID_FIELD,
            modified_field=DEFAULT_MODIFIED_FIELD,
            auth=None):
        query = """
        SELECT as_epoch(last_modified) AS last_modified, data
          FROM records
         WHERE id = :object_id
           AND parent_id = :parent_id
           AND collection_id = :collection_id;
        """
        placeholders = dict(object_id=object_id,
                            parent_id=parent_id,
                            collection_id=collection_id)
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            if result.rowcount == 0:
                raise exceptions.RecordNotFoundError(object_id)
            else:
                existing = result.fetchone()

        record = existing['data']
        record[id_field] = object_id
        record[modified_field] = existing['last_modified']
        return record

    def update(self, collection_id, parent_id, object_id, record,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):

        # Remove redundancy in data field
        query_record = {**record}
        query_record.pop(id_field, None)
        query_record.pop(modified_field, None)

        query = """
        WITH delete_potential_tombstone AS (
            DELETE FROM deleted
             WHERE id = :object_id
               AND parent_id = :parent_id
               AND collection_id = :collection_id
        )
        INSERT INTO records (id, parent_id, collection_id, data, last_modified)
        VALUES (:object_id, :parent_id,
                :collection_id, (:data)::JSONB,
                from_epoch(:last_modified))
        ON CONFLICT (id, parent_id, collection_id) DO UPDATE
            SET data=(:data)::JSONB,
                last_modified = GREATEST(from_epoch(:last_modified),
                                         EXCLUDED.last_modified)
        RETURNING as_epoch(last_modified) AS last_modified;
        """
        placeholders = dict(object_id=object_id,
                            parent_id=parent_id,
                            collection_id=collection_id,
                            last_modified=record.get(modified_field),
                            data=json.dumps(query_record))

        with self.client.connect() as conn:
            result = conn.execute(query, placeholders)
            updated = result.fetchone()

        record = {**record, id_field: object_id}
        record[modified_field] = updated['last_modified']
        return record

    def delete(self, collection_id, parent_id, object_id,
               id_field=DEFAULT_ID_FIELD, with_deleted=True,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None, last_modified=None):
        if with_deleted:
            query = """
            WITH deleted_record AS (
                DELETE
                FROM records
                WHERE id = :object_id
                  AND parent_id = :parent_id
                  AND collection_id = :collection_id
                RETURNING id
            )
            INSERT INTO deleted (id, parent_id, collection_id, last_modified)
            SELECT id, :parent_id, :collection_id, from_epoch(:last_modified)
              FROM deleted_record
            RETURNING as_epoch(last_modified) AS last_modified;
            """
        else:
            query = """
                DELETE
                FROM records
                WHERE id = :object_id
                  AND parent_id = :parent_id
                  AND collection_id = :collection_id
                RETURNING as_epoch(last_modified) AS last_modified;
            """
        placeholders = dict(object_id=object_id,
                            parent_id=parent_id,
                            collection_id=collection_id,
                            last_modified=last_modified)

        with self.client.connect() as conn:
            result = conn.execute(query, placeholders)
            if result.rowcount == 0:
                raise exceptions.RecordNotFoundError(object_id)
            inserted = result.fetchone()

        record = {}
        record[modified_field] = inserted['last_modified']
        record[id_field] = object_id

        record[deleted_field] = True
        return record

    def delete_all(self, collection_id, parent_id, filters=None,
                   sorting=None, pagination_rules=None, limit=None,
                   id_field=DEFAULT_ID_FIELD, with_deleted=True,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        if with_deleted:
            query = """
            WITH deleted_records AS (
                WITH matching_records AS (
                    SELECT id, parent_id, collection_id
                        FROM records
                        WHERE {parent_id_filter}
                              {collection_id_filter}
                              {conditions_filter}
                              {pagination_rules}
                        {sorting}
                        LIMIT :pagination_limit
                )
                DELETE
                FROM records
                USING matching_records
                WHERE records.id = matching_records.id
                  AND records.parent_id = matching_records.parent_id
                  AND records.collection_id = matching_records.collection_id
                RETURNING records.id, records.parent_id, records.collection_id
            )
            INSERT INTO deleted (id, parent_id, collection_id)
            SELECT id, parent_id, collection_id
              FROM deleted_records
            RETURNING id, as_epoch(last_modified) AS last_modified;
            """
        else:
            query = """
            WITH matching_records AS (
                SELECT id, parent_id, collection_id
                    FROM records
                    WHERE {parent_id_filter}
                          {collection_id_filter}
                          {conditions_filter}
                          {pagination_rules}
                    {sorting}
                    LIMIT :pagination_limit
            )
            DELETE
            FROM records
            USING matching_records
            WHERE records.id = matching_records.id
              AND records.parent_id = matching_records.parent_id
              AND records.collection_id = matching_records.collection_id
            RETURNING records.id, as_epoch(last_modified) AS last_modified;
            """

        id_field = id_field or self.id_field
        modified_field = modified_field or self.modified_field
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id)
        # Safe strings
        safeholders = defaultdict(str)
        # Handle parent_id as a regex only if it contains *
        if '*' in parent_id:
            safeholders['parent_id_filter'] = 'parent_id LIKE :parent_id'
            placeholders['parent_id'] = parent_id.replace('*', '%')
        else:
            safeholders['parent_id_filter'] = 'parent_id = :parent_id'
        # If collection is None, remove it from query.
        if collection_id is None:
            safeholders['collection_id_filter'] = ''
        else:
            safeholders['collection_id_filter'] = 'AND collection_id = :collection_id'  # NOQA

        if filters:
            safe_sql, holders = self._format_conditions(filters,
                                                        id_field,
                                                        modified_field)
            safeholders['conditions_filter'] = 'AND {}'.format(safe_sql)
            placeholders.update(**holders)

        if sorting:
            sql, holders = self._format_sorting(sorting, id_field,
                                                modified_field)
            safeholders['sorting'] = sql
            placeholders.update(**holders)

        if pagination_rules:
            sql, holders = self._format_pagination(pagination_rules, id_field,
                                                   modified_field)
            safeholders['pagination_rules'] = 'AND {}'.format(sql)
            placeholders.update(**holders)

        # Limit the number of results (pagination).
        limit = min(self._max_fetch_size, limit) if limit else self._max_fetch_size
        placeholders['pagination_limit'] = limit

        with self.client.connect() as conn:
            result = conn.execute(query.format_map(safeholders), placeholders)
            deleted = result.fetchmany(self._max_fetch_size)

        records = []
        for result in deleted:
            record = {}
            record[id_field] = result['id']
            record[modified_field] = result['last_modified']
            record[deleted_field] = True
            records.append(record)

        return records

    def purge_deleted(self, collection_id, parent_id, before=None,
                      id_field=DEFAULT_ID_FIELD,
                      modified_field=DEFAULT_MODIFIED_FIELD,
                      auth=None):
        delete_tombstones = """
        DELETE
        FROM deleted
        WHERE {parent_id_filter}
              {collection_id_filter}
              {conditions_filter}
        """
        id_field = id_field or self.id_field
        modified_field = modified_field or self.modified_field
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id)
        # Safe strings
        safeholders = defaultdict(str)
        # Handle parent_id as a regex only if it contains *
        if '*' in parent_id:
            safeholders['parent_id_filter'] = 'parent_id LIKE :parent_id'
            placeholders['parent_id'] = parent_id.replace('*', '%')
        else:
            safeholders['parent_id_filter'] = 'parent_id = :parent_id'
        # If collection is None, remove it from query.
        if collection_id is None:
            safeholders['collection_id_filter'] = ''
        else:
            safeholders['collection_id_filter'] = 'AND collection_id = :collection_id'  # NOQA

        if before is not None:
            safeholders['conditions_filter'] = (
                'AND as_epoch(last_modified) < :before')
            placeholders['before'] = before

        with self.client.connect() as conn:
            result = conn.execute(delete_tombstones.format_map(safeholders), placeholders)
            deleted = result.rowcount

            # If purging everything from a parent_id, then clear timestamps.
            if collection_id is None and before is None:
                delete_timestamps = """
                DELETE
                FROM timestamps
                WHERE {parent_id_filter}
                """
                conn.execute(delete_timestamps.format_map(safeholders), placeholders)

        return deleted

    def get_all(self, collection_id, parent_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False,
                id_field=DEFAULT_ID_FIELD,
                modified_field=DEFAULT_MODIFIED_FIELD,
                deleted_field=DEFAULT_DELETED_FIELD,
                auth=None):
        query = """
        WITH total_filtered AS (
            SELECT COUNT(id) AS count
              FROM records
             WHERE {parent_id_filter}
               AND collection_id = :collection_id
               {conditions_filter}
        ),
        collection_filtered AS (
            SELECT id, last_modified, data
              FROM records
             WHERE {parent_id_filter}
               AND collection_id = :collection_id
               {conditions_filter}
        ),
        fake_deleted AS (
            SELECT (:deleted_field)::JSONB AS data
        ),
        filtered_deleted AS (
            SELECT id, last_modified, fake_deleted.data AS data
              FROM deleted, fake_deleted
             WHERE {parent_id_filter}
               AND collection_id = :collection_id
               {conditions_filter}
               {deleted_limit}
        ),
        all_records AS (
            SELECT * FROM filtered_deleted
             UNION ALL
            SELECT * FROM collection_filtered
        ),
        paginated_records AS (
            SELECT DISTINCT id
              FROM all_records
              {pagination_rules}
        )
        SELECT total_filtered.count AS count_total,
               a.id, as_epoch(a.last_modified) AS last_modified, a.data
          FROM paginated_records AS p JOIN all_records AS a ON (a.id = p.id),
               total_filtered
          {sorting}
          LIMIT :pagination_limit;
        """
        deleted_field = json.dumps(dict([(deleted_field, True)]))

        # Unsafe strings escaped by PostgreSQL
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id,
                            deleted_field=deleted_field)

        # Safe strings
        safeholders = defaultdict(str)

        # Handle parent_id as a regex only if it contains *
        if '*' in parent_id:
            safeholders['parent_id_filter'] = 'parent_id LIKE :parent_id'
            placeholders['parent_id'] = parent_id.replace('*', '%')
        else:
            safeholders['parent_id_filter'] = 'parent_id = :parent_id'

        if filters:
            safe_sql, holders = self._format_conditions(filters,
                                                        id_field,
                                                        modified_field)
            safeholders['conditions_filter'] = 'AND {}'.format(safe_sql)
            placeholders.update(**holders)

        if not include_deleted:
            safeholders['deleted_limit'] = 'LIMIT 0'

        if sorting:
            sql, holders = self._format_sorting(sorting, id_field,
                                                modified_field)
            safeholders['sorting'] = sql
            placeholders.update(**holders)

        if pagination_rules:
            sql, holders = self._format_pagination(pagination_rules, id_field,
                                                   modified_field)
            safeholders['pagination_rules'] = 'WHERE {}'.format(sql)
            placeholders.update(**holders)

        # Limit the number of results (pagination).
        limit = min(self._max_fetch_size, limit) if limit else self._max_fetch_size
        placeholders['pagination_limit'] = limit

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query.format_map(safeholders), placeholders)
            retrieved = result.fetchmany(self._max_fetch_size)

        if len(retrieved) == 0:
            return [], 0

        count_total = retrieved[0]['count_total']

        records = []
        for result in retrieved:
            record = result['data']
            record[id_field] = result['id']
            record[modified_field] = result['last_modified']
            records.append(record)

        return records, count_total

    def _format_conditions(self, filters, id_field, modified_field,
                           prefix='filters'):
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
            COMPARISON.EQ: '=',
            COMPARISON.NOT: '<>',
            COMPARISON.IN: 'IN',
            COMPARISON.EXCLUDE: 'NOT IN',
            COMPARISON.LIKE: 'ILIKE',
        }

        conditions = []
        holders = {}
        for i, filtr in enumerate(filters):
            value = filtr.value
            is_like_query = filtr.operator == COMPARISON.LIKE

            if filtr.field == id_field:
                sql_field = 'id'
                if isinstance(value, int):
                    value = str(value)
            elif filtr.field == modified_field:
                sql_field = 'as_epoch(last_modified)'
            else:
                column_name = "data"
                # Subfields: ``person.name`` becomes ``data->person->>name``
                subfields = filtr.field.split('.')
                for j, subfield in enumerate(subfields):
                    # Safely escape field name
                    field_holder = '{}_field_{}_{}'.format(prefix, i, j)
                    holders[field_holder] = subfield
                    # Use ->> to convert the last level to text if
                    # needed for LIKE query. (Other queries do JSONB comparison.)
                    column_name += "->>" if j == len(subfields) - 1 and is_like_query else "->"
                    column_name += ":{}".format(field_holder)

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
                )
                null_true_operators = (
                    # NULLs are automatically not equal to everything.
                    COMPARISON.NOT,
                    # Thus they can never be excluded.
                    COMPARISON.EXCLUDE,
                    # Match Postgres's default sort behavior
                    # (NULLS LAST) by allowing NULLs to
                    # automatically be greater than everything.
                    COMPARISON.GT, COMPARISON.MIN,
                )

                if filtr.operator in null_false_operators:
                    sql_field = "{} IS NOT NULL AND {}".format(column_name, column_name)
                elif filtr.operator in null_true_operators:
                    sql_field = "{} IS NULL OR {}".format(column_name, column_name)
                else:
                    # No need to check for LT and MAX because NULL < foo
                    # is NULL, which is falsy in SQL.
                    sql_field = column_name

            string_field = filtr.field in (id_field, modified_field) or is_like_query
            if not string_field:
                # JSONB-ify the value.
                if filtr.operator not in (COMPARISON.IN, COMPARISON.EXCLUDE):
                    value = json.dumps(value)
                else:
                    value = [json.dumps(v) for v in value]

            if filtr.operator in (COMPARISON.IN, COMPARISON.EXCLUDE):
                value = tuple(value)
                # WHERE field IN ();  -- Fails with syntax error.
                if len(value) == 0:
                    value = (None,)

            if is_like_query:
                # Operand should be a string.
                # Add implicit start/end wildchars if none is specified.
                if "*" not in value:
                    value = "*{}*".format(value)
                value = value.replace("*", "%")

            if filtr.operator == COMPARISON.HAS:
                operator = 'IS NOT NULL' if filtr.value else 'IS NULL'
                cond = "{} {}".format(sql_field, operator)
            else:
                # Safely escape value
                value_holder = '{}_value_{}'.format(prefix, i)
                holders[value_holder] = value

                sql_operator = operators.setdefault(filtr.operator,
                                                    filtr.operator.value)
                cond = "{} {} :{}".format(sql_field, sql_operator, value_holder)
            conditions.append(cond)

        safe_sql = ' AND '.join(conditions)
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
            prefix = 'rules_{}'.format(i)
            safe_sql, holders = self._format_conditions(rule,
                                                        id_field,
                                                        modified_field,
                                                        prefix=prefix)
            rules.append(safe_sql)
            placeholders.update(**holders)

        safe_sql = ' OR '.join(['({})'.format(r) for r in rules])
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
                sql_field = 'id'
            elif sort.field == modified_field:
                sql_field = 'last_modified'
            else:
                # Subfields: ``person.name`` becomes ``data->person->>name``
                subfields = sort.field.split('.')
                sql_field = 'data'
                for j, subfield in enumerate(subfields):
                    # Safely escape field name
                    field_holder = 'sort_field_{}_{}'.format(i, j)
                    holders[field_holder] = subfield
                    # Use ->> to convert the last level to text.
                    sql_field += '->(:{})'.format(field_holder)

            sql_direction = 'ASC' if sort.direction > 0 else 'DESC'
            sql_sort = "{} {}".format(sql_field, sql_direction)
            sorts.append(sql_sort)

        safe_sql = 'ORDER BY {}'.format(', '.join(sorts))
        return safe_sql, holders


def load_from_config(config):
    settings = config.get_settings()
    max_fetch_size = int(settings['storage_max_fetch_size'])
    client = create_from_config(config, prefix='storage_')
    return Storage(client=client, max_fetch_size=max_fetch_size)
