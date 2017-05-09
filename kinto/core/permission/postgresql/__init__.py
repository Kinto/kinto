import logging
import os

from collections import OrderedDict

from kinto.core.permission import PermissionBase
from kinto.core.storage.postgresql.client import create_from_config


logger = logging.getLogger(__name__)


class Permission(PermissionBase):
    """Permission backend using PostgreSQL.

    Enable in configuration::

        kinto.permission_backend = kinto.core.permission.postgresql

    Database location URI can be customized::

        kinto.permission_url = postgres://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in :file:`~/.pgpass` (*see PostgreSQL documentation*).

    .. note::

        Some tables and indices are created when ``kinto migrate`` is run.
        This requires some privileges on the database, or some error will
        be raised.

        **Alternatively**, the schema can be initialized outside the
        python application, using the SQL file located in
        :file:`kinto/core/permission/postgresql/schema.sql`. This allows to
        distinguish schema manipulation privileges from schema usage.


    A connection pool is enabled by default::

        kinto.permission_pool_size = 10
        kinto.permission_maxoverflow = 10
        kinto.permission_max_backlog = -1
        kinto.permission_pool_recycle = -1
        kinto.permission_pool_timeout = 30
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

    :noindex:
    """  # NOQA
    def __init__(self, client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client

    def initialize_schema(self, dry_run=False):
        # Check if user_principals table exists.
        query = """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'user_principals';
        """
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            if result.rowcount > 0:
                logger.info("PostgreSQL permission schema is up-to-date.")
                return

        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        sql_file = os.path.join(here, 'schema.sql')

        if dry_run:
            logger.info("Create permission schema from '{}'".format(sql_file))
            return

        # Since called outside request, force commit.
        with open(sql_file) as f:
            schema = f.read()
        with self.client.connect(force_commit=True) as conn:
            conn.execute(schema)
        logger.info('Created PostgreSQL permission tables')

    def flush(self):
        query = """
        DELETE FROM user_principals;
        DELETE FROM access_control_entries;
        """
        # Since called outside request (e.g. tests), force commit.
        with self.client.connect(force_commit=True) as conn:
            conn.execute(query)
        logger.debug('Flushed PostgreSQL permission tables')

    def add_user_principal(self, user_id, principal):
        query = """
        INSERT INTO user_principals (user_id, principal)
        SELECT :user_id, :principal
         WHERE NOT EXISTS (
            SELECT principal
            FROM user_principals
            WHERE user_id = :user_id
              AND principal = :principal
        );"""
        with self.client.connect() as conn:
            conn.execute(query, dict(user_id=user_id, principal=principal))

    def remove_user_principal(self, user_id, principal):
        query = """
        DELETE FROM user_principals
         WHERE user_id = :user_id
           AND principal = :principal;"""
        with self.client.connect() as conn:
            conn.execute(query, dict(user_id=user_id, principal=principal))

    def remove_principal(self, principal):
        query = """
        DELETE FROM user_principals
         WHERE principal = :principal;"""
        with self.client.connect() as conn:
            conn.execute(query, dict(principal=principal))

    def get_user_principals(self, user_id):
        query = """
        SELECT principal
          FROM user_principals
         WHERE user_id = :user_id
            OR user_id = 'system.Authenticated';"""
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, dict(user_id=user_id))
            results = result.fetchall()
        return set([r['principal'] for r in results])

    def add_principal_to_ace(self, object_id, permission, principal):
        query = """
        INSERT INTO access_control_entries (object_id, permission, principal)
        SELECT :object_id, :permission, :principal
         WHERE NOT EXISTS (
            SELECT principal
              FROM access_control_entries
             WHERE object_id = :object_id
               AND permission = :permission
               AND principal = :principal
        );"""
        with self.client.connect() as conn:
            conn.execute(query, dict(object_id=object_id,
                                     permission=permission,
                                     principal=principal))

    def remove_principal_from_ace(self, object_id, permission, principal):
        query = """
        DELETE FROM access_control_entries
         WHERE object_id = :object_id
           AND permission = :permission
           AND principal = :principal;"""
        with self.client.connect() as conn:
            conn.execute(query, dict(object_id=object_id,
                                     permission=permission,
                                     principal=principal))

    def get_object_permission_principals(self, object_id, permission):
        query = """
        SELECT principal
          FROM access_control_entries
         WHERE object_id = :object_id
           AND permission = :permission;"""
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, dict(object_id=object_id,
                                              permission=permission))
            results = result.fetchall()
        return set([r['principal'] for r in results])

    def get_authorized_principals(self, bound_permissions):
        # XXX: this method is not used, except in test suites :(
        if not bound_permissions:
            return set()

        placeholders = {}
        perm_values = []
        for i, (obj, perm) in enumerate(bound_permissions):
            placeholders['obj_{}'.format(i)] = obj
            placeholders['perm_{}'.format(i)] = perm
            perm_values.append("(:obj_{0}, :perm_{0})".format(i))

        query = """
        WITH required_perms AS (
          VALUES {}
        )
        SELECT principal
          FROM required_perms JOIN access_control_entries
            ON (object_id = column1 AND permission = column2);
        """.format(','.join(perm_values))
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            results = result.fetchall()
        return set([r['principal'] for r in results])

    def get_accessible_objects(self, principals, bound_permissions=None, with_children=True):
        placeholders = {}

        if bound_permissions is None:
            # Return all objects on which the specified principals have some
            # permissions.
            # (e.g. permissions endpoint which lists everything)
            query = """
            SELECT object_id, permission
              FROM access_control_entries
             WHERE principal IN :principals
            """
            placeholders['principals'] = tuple(principals)

        elif len(bound_permissions) == 0:
            # If the list of object permissions to filter on is empty, then
            # do not bother querying the backend. The result will be empty.
            # (e.g. root object /buckets)
            return {}
        else:
            principals_values = []
            for i, principal in enumerate(principals):
                placeholders['principal_{}'.format(i)] = principal
                principals_values.append("(:principal_{})".format(i))

            perm_values = []
            for i, (obj, perm) in enumerate(bound_permissions):
                placeholders['obj_{}'.format(i)] = obj.replace('*', '%')
                placeholders['perm_{}'.format(i)] = perm
                perm_values.append("(:obj_{0}, :perm_{0})".format(i))

            if with_children:
                object_id_condition = 'object_id LIKE pattern'
            else:
                object_id_condition = ("object_id LIKE pattern "
                                       "AND object_id NOT LIKE pattern || '/%'")
            query = """
            WITH required_perms AS (
              VALUES {perms}
            ),
            user_principals AS (
              VALUES {principals}
            ),
            potential_objects AS (
              SELECT object_id, permission, required_perms.column1 AS pattern
                FROM access_control_entries
                JOIN user_principals
                  ON (principal = user_principals.column1)
                JOIN required_perms
                  ON (permission = required_perms.column2)
            )
            SELECT object_id, permission
              FROM potential_objects
             WHERE {object_id_condition};
            """.format(perms=','.join(perm_values),
                       principals=','.join(principals_values),
                       object_id_condition=object_id_condition)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            results = result.fetchall()

        perms_by_id = {}
        for r in results:
            perms_by_id.setdefault(r['object_id'], set()).add(r['permission'])
        return perms_by_id

    def check_permission(self, principals, bound_permissions):
        if not bound_permissions:
            return False

        placeholders = {}
        perms_values = []
        for i, (obj, perm) in enumerate(bound_permissions):
            placeholders['obj_{}'.format(i)] = obj
            placeholders['perm_{}'.format(i)] = perm
            perms_values.append("(:obj_{0}, :perm_{0})".format(i))

        principals_values = []
        for i, principal in enumerate(principals):
            placeholders['principal_{}'.format(i)] = principal
            principals_values.append("(:principal_{})".format(i))

        query = """
        WITH required_perms AS (
          VALUES {perms}
        ),
        allowed_principals AS (
          SELECT principal
            FROM required_perms JOIN access_control_entries
              ON (object_id = column1 AND permission = column2)
        ),
        required_principals AS (
          VALUES {principals}
        )
        SELECT COUNT(*) AS matched
          FROM required_principals JOIN allowed_principals
            ON (required_principals.column1 = principal);
        """.format(perms=','.join(perms_values),
                   principals=','.join(principals_values))

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            total = result.fetchone()
        return total['matched'] > 0

    def get_objects_permissions(self, objects_ids, permissions=None):
        object_ids_values = []
        placeholders = {}
        for i, obj_id in enumerate(objects_ids):
            object_ids_values.append("({0}, :obj_id_{0})".format(i))
            placeholders['obj_id_{}'.format(i)] = obj_id

        query = """
        WITH required_object_ids AS (
          VALUES {objects_ids}
        )
        SELECT object_id, permission, principal
            FROM required_object_ids JOIN access_control_entries
              ON (object_id = column2)
              {permissions_condition}
        ORDER BY column1 ASC;
        """
        safeholders = {
            'objects_ids': ','.join(object_ids_values),
            'permissions_condition': ''
        }
        if permissions is not None:
            safeholders['permissions_condition'] = """
              WHERE permission IN :permissions"""
            placeholders["permissions"] = tuple(permissions)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query.format_map(safeholders), placeholders)
            rows = result.fetchall()

        groupby_id = OrderedDict()
        for object_id in objects_ids:
            groupby_id[object_id] = {}
        for row in rows:
            object_id, permission, principal = (row['object_id'],
                                                row['permission'],
                                                row['principal'])
            groupby_id[object_id].setdefault(permission, set()).add(principal)
        return list(groupby_id.values())

    def replace_object_permissions(self, object_id, permissions):
        if not permissions:
            return

        placeholders = {
            'object_id': object_id
        }

        new_aces = []
        specified_perms = []
        for i, (perm, principals) in enumerate(permissions.items()):
            placeholders['perm_{}'.format(i)] = perm
            specified_perms.append("(:perm_{})".format(i))
            for principal in set(principals):
                j = len(new_aces)
                placeholders['principal_{}'.format(j)] = principal
                new_aces.append("(:perm_{}, :principal_{})".format(i, j))

        if not new_aces:
            query = """
            WITH specified_perms AS (
              VALUES {specified_perms}
            )
            DELETE FROM access_control_entries
             USING specified_perms
             WHERE object_id = :object_id AND permission = column1
            """.format(specified_perms=','.join(specified_perms))

        else:
            query = """
            WITH specified_perms AS (
              VALUES {specified_perms}
            ),
            delete_specified AS (
              DELETE FROM access_control_entries
               USING specified_perms
               WHERE object_id = :object_id AND permission = column1
               RETURNING object_id
            ),
            affected_object AS (
              SELECT object_id FROM delete_specified
              UNION SELECT :object_id
            ),
            new_aces AS (
              VALUES {new_aces}
            )
            INSERT INTO access_control_entries(object_id, permission, principal)
              SELECT DISTINCT d.object_id, n.column1, n.column2
                FROM new_aces AS n, affected_object AS d;
            """.format(specified_perms=','.join(specified_perms),
                       new_aces=','.join(new_aces))

        with self.client.connect() as conn:
            conn.execute(query, placeholders)

    def delete_object_permissions(self, *object_id_list):
        if len(object_id_list) == 0:
            return

        object_ids_values = []
        placeholders = {}
        for i, obj_id in enumerate(object_id_list):
            object_ids_values.append("(:obj_id_{})".format(i))
            placeholders['obj_id_{}'.format(i)] = obj_id.replace('*', '%')

        query = """
        WITH object_ids AS (
          VALUES {object_ids_values}
        )
        DELETE FROM access_control_entries
         USING object_ids
         WHERE object_id LIKE column1;"""
        safeholders = {
            'object_ids_values': ','.join(object_ids_values)
        }
        with self.client.connect() as conn:
            conn.execute(query.format_map(safeholders), placeholders)


def load_from_config(config):
    client = create_from_config(config, prefix='permission_')
    return Permission(client=client)
