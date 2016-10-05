from __future__ import absolute_import

import os

from collections import OrderedDict

from kinto.core import logger
from kinto.core.permission import PermissionBase
from kinto.core.storage.postgresql.client import create_from_config


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
        super(Permission, self).__init__(*args, **kwargs)
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
            logger.info("Create permission schema from %s" % sql_file)
            return

        # Since called outside request, force commit.
        schema = open(sql_file).read()
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

        perm_values = ','.join(["('%s', '%s')" % p for p in bound_permissions])
        query = """
        WITH required_perms AS (
          VALUES %s
        )
        SELECT principal
          FROM required_perms JOIN access_control_entries
            ON (object_id = column1 AND permission = column2);
        """ % perm_values
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            results = result.fetchall()
        return set([r['principal'] for r in results])

    def get_accessible_objects(self, principals, bound_permissions=None):
        principals_values = ','.join(["('%s')" % p for p in principals])
        if bound_permissions is None:
            query = """
            WITH user_principals AS (
              VALUES %(principals)s
            )
            SELECT object_id, permission
              FROM access_control_entries
              JOIN user_principals
                ON (principal = user_principals.column1);
            """ % dict(principals=principals_values)
        else:
            perms = [(o.replace('*', '.*'), p) for (o, p) in bound_permissions]
            perms_values = ','.join(["('%s', '%s')" % p for p in perms])
            query = """
            WITH required_perms AS (
              VALUES %(perms)s
            ),
            user_principals AS (
              VALUES %(principals)s
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
             WHERE object_id ~ pattern;
            """ % dict(perms=perms_values,
                       principals=principals_values)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            results = result.fetchall()

        perms_by_id = {}
        for r in results:
            perms_by_id.setdefault(r['object_id'], set()).add(r['permission'])
        return perms_by_id

    def check_permission(self, principals, bound_permissions):
        if not bound_permissions:
            return False

        principals_values = ','.join(["('%s')" % p for p in principals])
        perm_values = ','.join(["('%s', '%s')" % p for p in bound_permissions])
        query = """
        WITH required_perms AS (
          VALUES %(perms)s
        ),
        allowed_principals AS (
          SELECT principal
            FROM required_perms JOIN access_control_entries
              ON (object_id = column1 AND permission = column2)
        ),
        required_principals AS (
          VALUES %(principals)s
        )
        SELECT COUNT(*) AS matched
          FROM required_principals JOIN allowed_principals
            ON (required_principals.column1 = principal);
        """ % dict(perms=perm_values, principals=principals_values)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            total = result.fetchone()
        return total['matched'] > 0

    def get_objects_permissions(self, objects_ids, permissions=None):
        query = """
        WITH required_object_ids AS (
          VALUES %(objects_ids)s
        )
        SELECT object_id, permission, principal
            FROM required_object_ids JOIN access_control_entries
              ON (object_id = column2)
              %(permissions_condition)s
        ORDER BY column1 ASC;
        """
        obj_ids_values = ','.join(["(%s, '%s')" % t
                                   for t in enumerate(objects_ids)])
        safeholders = {
            'objects_ids': obj_ids_values,
            'permissions_condition': ''
        }
        placeholders = {}
        if permissions is not None:
            safeholders['permissions_condition'] = """
              WHERE permission IN :permissions"""
            placeholders["permissions"] = tuple(permissions)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query % safeholders, placeholders)
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

        new_perms = []
        specified_perms = []
        for i, (perm, principals) in enumerate(permissions.items()):
            placeholders['perm_%s' % i] = perm
            specified_perms.append("(:perm_%s)" % i)
            for principal in set(principals):
                j = len(new_perms)
                placeholders['principal_%s' % j] = principal
                new_perms.append("(:perm_%s, :principal_%s)" % (i, j))

        delete_query = """
        WITH specified_perms AS (
          VALUES %(specified_perms)s
        )
        DELETE FROM access_control_entries
         USING specified_perms
         WHERE object_id = :object_id AND permission = column1
        """ % dict(specified_perms=','.join(specified_perms))

        insert_query = """
        WITH new_aces AS (
          VALUES %(new_perms)s
        )
        INSERT INTO access_control_entries(object_id, permission, principal)
          SELECT :object_id, column1, column2
            FROM new_aces;
        """ % dict(new_perms=','.join(new_perms))

        with self.client.connect() as conn:
            conn.execute(delete_query, placeholders)
            if new_perms:
                conn.execute(insert_query, placeholders)

    def delete_object_permissions(self, *object_id_list):
        if len(object_id_list) == 0:
            return

        query = """
        DELETE FROM access_control_entries
         WHERE object_id IN :object_id_list;"""
        with self.client.connect() as conn:
            conn.execute(query, dict(object_id_list=tuple(object_id_list)))


def load_from_config(config):
    client = create_from_config(config, prefix='permission_')
    return Permission(client=client)
