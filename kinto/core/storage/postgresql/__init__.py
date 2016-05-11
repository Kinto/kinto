import os
import warnings
from collections import defaultdict

import six

from kinto.core import logger
from kinto.core.storage import (
    StorageBase, exceptions, Filter,
    DEFAULT_ID_FIELD, DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD)
from kinto.core.storage.postgresql.client import create_from_config
from kinto.core.utils import COMPARISON, json


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
        kinto.cache_poolclass = kinto.core.storage.postgresql.pool.QueuePoolWithMaxBacklog

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

    schema_version = 11

    def __init__(self, client, max_fetch_size, *args, **kwargs):
        super(Storage, self).__init__(*args, **kwargs)
        self.client = client
        self._max_fetch_size = max_fetch_size

    def _execute_sql_file(self, filepath):
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, filepath)).read()
        # Since called outside request, force commit.
        with self.client.connect(force_commit=True) as conn:
            conn.execute(schema)

    def initialize_schema(self):
        """Create PostgreSQL tables, and run necessary schema migrations.

        .. note::

            Relies on JSONB fields, available in recent versions of PostgreSQL.
        """
        version = self._get_installed_version()
        if not version:
            # Create full schema.
            self._check_database_encoding()
            self._check_database_timezone()
            # Create full schema.
            self._execute_sql_file('schema.sql')
            logger.info('Created PostgreSQL storage tables '
                        '(version %s).' % self.schema_version)
            return

        logger.debug('Detected PostgreSQL schema version %s.' % version)
        migrations = [(v, v + 1) for v in range(version, self.schema_version)]
        if not migrations:
            logger.info('Schema is up-to-date.')

        for migration in migrations:
            # Check order of migrations.
            expected = migration[0]
            current = self._get_installed_version()
            error_msg = "Expected version %s. Found version %s."
            if expected != current:
                raise AssertionError(error_msg % (expected, current))

            logger.info('Migrate schema from version %s to %s.' % migration)
            filepath = 'migration_%03d_%03d.sql' % migration
            self._execute_sql_file(os.path.join('migrations', filepath))

        logger.info('Schema migration done.')

    def _check_database_timezone(self):
        # Make sure database has UTC timezone.
        query = "SELECT current_setting('TIMEZONE') AS timezone;"
        with self.client.connect() as conn:
            result = conn.execute(query)
            record = result.fetchone()
        timezone = record['timezone'].upper()
        if timezone != 'UTC':  # pragma: no cover
            msg = 'Database timezone is not UTC (%s)' % timezone
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
            raise AssertionError('Unexpected database encoding %s' % encoding)

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
                    error_msg = 'Missing schema history: consider version %s.'
                    logger.warning(error_msg % self.schema_version)
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
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        id_generator = id_generator or self.id_generator
        record = record.copy()
        record_id = record.setdefault(id_field, id_generator())

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
        RETURNING id, as_epoch(last_modified) AS last_modified;
        """
        placeholders = dict(object_id=record_id,
                            parent_id=parent_id,
                            collection_id=collection_id,
                            last_modified=record.get(modified_field),
                            data=json.dumps(record))
        with self.client.connect() as conn:
            # Check that it does violate the resource unicity rules.
            self._check_unicity(conn, collection_id, parent_id, record,
                                unique_fields, id_field, modified_field,
                                for_creation=True)
            result = conn.execute(query, placeholders)
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
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        query_create = """
        INSERT INTO records (id, parent_id, collection_id, data, last_modified)
        VALUES (:object_id, :parent_id,
                :collection_id, (:data)::JSONB,
                from_epoch(:last_modified))
        RETURNING as_epoch(last_modified) AS last_modified;
        """

        query_update = """
        UPDATE records SET data=(:data)::JSONB,
                           last_modified=from_epoch(:last_modified)
        WHERE id = :object_id
           AND parent_id = :parent_id
           AND collection_id = :collection_id
        RETURNING as_epoch(last_modified) AS last_modified;
        """
        placeholders = dict(object_id=object_id,
                            parent_id=parent_id,
                            collection_id=collection_id,
                            last_modified=record.get(modified_field),
                            data=json.dumps(record))

        record = record.copy()
        record[id_field] = object_id

        with self.client.connect() as conn:
            # Check that it does violate the resource unicity rules.
            self._check_unicity(conn, collection_id, parent_id, record,
                                unique_fields, id_field, modified_field)
            # Create or update ?
            query = """
            SELECT id FROM records
            WHERE id = :object_id
              AND parent_id = :parent_id
              AND collection_id = :collection_id;
            """
            result = conn.execute(query, placeholders)
            query = query_update if result.rowcount > 0 else query_create

            result = conn.execute(query, placeholders)
            updated = result.fetchone()

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
                   id_field=DEFAULT_ID_FIELD, with_deleted=True,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        if with_deleted:
            query = """
            WITH deleted_records AS (
                DELETE
                FROM records
                WHERE parent_id = :parent_id
                  AND collection_id = :collection_id
                  %(conditions_filter)s
                RETURNING id
            )
            INSERT INTO deleted (id, parent_id, collection_id)
            SELECT id, :parent_id, :collection_id
              FROM deleted_records
            RETURNING id, as_epoch(last_modified) AS last_modified;
            """
        else:
            query = """
                DELETE
                FROM records
                WHERE parent_id = :parent_id
                  AND collection_id = :collection_id
                  %(conditions_filter)s
                RETURNING id, as_epoch(last_modified) AS last_modified;
            """
        id_field = id_field or self.id_field
        modified_field = modified_field or self.modified_field
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id)
        # Safe strings
        safeholders = defaultdict(six.text_type)

        if filters:
            safe_sql, holders = self._format_conditions(filters,
                                                        id_field,
                                                        modified_field)
            safeholders['conditions_filter'] = 'AND %s' % safe_sql
            placeholders.update(**holders)

        with self.client.connect() as conn:
            result = conn.execute(query % safeholders, placeholders)
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
        query = """
        DELETE
        FROM deleted
        WHERE parent_id = :parent_id
          AND collection_id = :collection_id
          %(conditions_filter)s;
        """
        id_field = id_field or self.id_field
        modified_field = modified_field or self.modified_field
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id)
        # Safe strings
        safeholders = defaultdict(six.text_type)

        if before is not None:
            safeholders['conditions_filter'] = (
                'AND as_epoch(last_modified) < :before')
            placeholders['before'] = before

        with self.client.connect() as conn:
            result = conn.execute(query % safeholders, placeholders)

        return result.rowcount

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
             WHERE parent_id = :parent_id
               AND collection_id = :collection_id
               %(conditions_filter)s
        ),
        collection_filtered AS (
            SELECT id, last_modified, data
              FROM records
             WHERE parent_id = :parent_id
               AND collection_id = :collection_id
               %(conditions_filter)s
             LIMIT %(max_fetch_size)s
        ),
        fake_deleted AS (
            SELECT (:deleted_field)::JSONB AS data
        ),
        filtered_deleted AS (
            SELECT id, last_modified, fake_deleted.data AS data
              FROM deleted, fake_deleted
             WHERE parent_id = :parent_id
               AND collection_id = :collection_id
               %(conditions_filter)s
               %(deleted_limit)s
        ),
        all_records AS (
            SELECT * FROM filtered_deleted
             UNION ALL
            SELECT * FROM collection_filtered
        ),
        paginated_records AS (
            SELECT DISTINCT id
              FROM all_records
              %(pagination_rules)s
        )
        SELECT total_filtered.count AS count_total,
               a.id, as_epoch(a.last_modified) AS last_modified, a.data
          FROM paginated_records AS p JOIN all_records AS a ON (a.id = p.id),
               total_filtered
          %(sorting)s
          %(pagination_limit)s;
        """
        deleted_field = json.dumps(dict([(deleted_field, True)]))

        # Unsafe strings escaped by PostgreSQL
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id,
                            deleted_field=deleted_field)

        # Safe strings
        safeholders = defaultdict(six.text_type)
        safeholders['max_fetch_size'] = self._max_fetch_size

        if filters:
            safe_sql, holders = self._format_conditions(filters,
                                                        id_field,
                                                        modified_field)
            safeholders['conditions_filter'] = 'AND %s' % safe_sql
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
            safeholders['pagination_rules'] = 'WHERE %s' % sql
            placeholders.update(**holders)

        if limit:
            assert isinstance(limit, six.integer_types)  # asserted in resource
            safeholders['pagination_limit'] = 'LIMIT %s' % limit

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query % safeholders, placeholders)
            retrieved = result.fetchmany(self._max_fetch_size)

        if not len(retrieved):
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
        }

        conditions = []
        holders = {}
        for i, filtr in enumerate(filters):
            value = filtr.value

            if filtr.field == id_field:
                sql_field = 'id'
            elif filtr.field == modified_field:
                sql_field = 'as_epoch(last_modified)'
            else:
                # Safely escape field name
                field_holder = '%s_field_%s' % (prefix, i)
                holders[field_holder] = filtr.field

                # JSON operator ->> retrieves values as text.
                # If field is missing, we default to ''.
                sql_field = "coalesce(data->>:%s, '')" % field_holder
                if isinstance(value, (int, float)) and \
                   value not in (True, False):
                    sql_field = "(data->>:%s)::numeric" % field_holder

            if filtr.operator not in (COMPARISON.IN, COMPARISON.EXCLUDE):
                # For the IN operator, let psycopg escape the values list.
                # Otherwise JSON-ify the native value (e.g. True -> 'true')
                if not isinstance(filtr.value, six.string_types):
                    value = json.dumps(filtr.value).strip('"')
            else:
                value = tuple(value)

            # Safely escape value
            value_holder = '%s_value_%s' % (prefix, i)
            holders[value_holder] = value

            sql_operator = operators.setdefault(filtr.operator,
                                                filtr.operator.value)
            cond = "%s %s :%s" % (sql_field, sql_operator, value_holder)
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
            prefix = 'rules_%s' % i
            safe_sql, holders = self._format_conditions(rule,
                                                        id_field,
                                                        modified_field,
                                                        prefix=prefix)
            rules.append(safe_sql)
            placeholders.update(**holders)

        safe_sql = ' OR '.join(['(%s)' % r for r in rules])
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
                field_holder = 'sort_field_%s' % i
                holders[field_holder] = sort.field
                sql_field = 'data->(:%s)' % field_holder

            sql_direction = 'ASC' if sort.direction > 0 else 'DESC'
            sql_sort = "%s %s" % (sql_field, sql_direction)
            sorts.append(sql_sort)

        safe_sql = 'ORDER BY %s' % (', '.join(sorts))
        return safe_sql, holders

    def _check_unicity(self, conn, collection_id, parent_id, record,
                       unique_fields, id_field, modified_field,
                       for_creation=False):
        """Check that no existing record (in the current transaction snapshot)
        violates the resource unicity rules.
        """
        # If id is provided by client, check that no record conflicts.
        if for_creation and id_field in record:
            unique_fields = (unique_fields or tuple()) + (id_field,)

        if not unique_fields:
            return

        query = """
        SELECT id
          FROM records
         WHERE parent_id = :parent_id
           AND collection_id = :collection_id
           AND (%(conditions_filter)s)
           AND %(condition_record)s
         LIMIT 1;
        """
        safeholders = dict()
        placeholders = dict(parent_id=parent_id,
                            collection_id=collection_id)

        # Transform each field unicity into a query condition.
        filters = []
        for field in set(unique_fields):
            value = record.get(field)
            if value is None:
                continue
            sql, holders = self._format_conditions(
                [Filter(field, value, COMPARISON.EQ)],
                id_field,
                modified_field,
                prefix=field)
            filters.append(sql)
            placeholders.update(**holders)

        # All unique fields are empty in record
        if not filters:
            return

        safeholders['conditions_filter'] = ' OR '.join(filters)

        # If record is in database, then exclude it of unicity check.
        if not for_creation:
            object_id = record[id_field]
            sql, holders = self._format_conditions(
                [Filter(id_field, object_id, COMPARISON.NOT)],
                id_field,
                modified_field)
            safeholders['condition_record'] = sql
            placeholders.update(**holders)
        else:
            safeholders['condition_record'] = 'TRUE'

        result = conn.execute(query % safeholders, placeholders)
        if result.rowcount > 0:
            existing = result.fetchone()
            record = self.get(collection_id, parent_id, existing['id'])
            raise exceptions.UnicityError(unique_fields[0], record)


def load_from_config(config):
    settings = config.get_settings()
    max_fetch_size = int(settings['storage_max_fetch_size'])
    client = create_from_config(config, prefix='storage_')
    return Storage(client=client, max_fetch_size=max_fetch_size)
