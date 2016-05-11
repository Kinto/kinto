from __future__ import absolute_import

import os

from collections import defaultdict

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

    :noindex:
    """  # NOQA
    def __init__(self, client, *args, **kwargs):
        super(Permission, self).__init__(*args, **kwargs)
        self.client = client

    def initialize_schema(self):
        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, 'schema.sql')).read()
        # Since called outside request, force commit.
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

    def user_principals(self, user_id):
        query = """
        SELECT principal
          FROM user_principals
         WHERE user_id = :user_id;"""
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

    def object_permission_principals(self, object_id, permission):
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

    def object_permission_authorized_principals(self, object_id, permission,
                                                get_bound_permissions=None):
        # XXX: this method is not used, except in test suites :(
        if get_bound_permissions is None:
            perms = [(object_id, permission)]
        else:
            perms = get_bound_permissions(object_id, permission)

        if not perms:
            return set()

        perms_values = ','.join(["('%s', '%s')" % p for p in perms])
        query = """
        WITH required_perms AS (
          VALUES %s
        )
        SELECT principal
          FROM required_perms JOIN access_control_entries
            ON (object_id = column1 AND permission = column2);
        """ % perms_values
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            results = result.fetchall()
        return set([r['principal'] for r in results])

    def principals_accessible_objects(self, principals, permission,
                                      object_id_match=None,
                                      get_bound_permissions=None):
        placeholders = {'permission': permission}

        if object_id_match is None:
            object_id_match = '*'

        if get_bound_permissions is None:
            perms = [(object_id_match, permission)]
        else:
            perms = get_bound_permissions(object_id_match, permission)

        perms = [(o.replace('*', '.*'), p) for (o, p) in perms
                 if o.endswith(object_id_match)]
        perms_values = ','.join(["('%s', '%s')" % p for p in perms])
        principals_values = ','.join(["('%s')" % p for p in principals])
        query = """
        WITH required_perms AS (
          VALUES %(perms)s
        ),
        user_principals AS (
          VALUES %(principals)s
        ),
        potential_objects AS (
          SELECT object_id, required_perms.column1 AS pattern
            FROM access_control_entries
            JOIN user_principals
              ON (principal = user_principals.column1)
            JOIN required_perms
              ON (permission = required_perms.column2)
        )
        SELECT object_id
          FROM potential_objects
         WHERE object_id ~ pattern;
        """ % dict(perms=perms_values,
                   principals=principals_values)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            results = result.fetchall()
        return set([r['object_id'] for r in results])

    def check_permission(self, object_id, permission, principals,
                         get_bound_permissions=None):
        if get_bound_permissions is None:
            perms = [(object_id, permission)]
        else:
            perms = get_bound_permissions(object_id, permission)

        if not perms:
            return False

        perms_values = ','.join(["('%s', '%s')" % p for p in perms])
        principals_values = ','.join(["('%s')" % p for p in principals])
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
        """ % dict(perms=perms_values, principals=principals_values)

        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            total = result.fetchone()
        return total['matched'] > 0

    def object_permissions(self, object_id, permissions=None):
        query = """
        SELECT permission, principal
        FROM access_control_entries
        WHERE object_id = :object_id"""

        placeholders = dict(object_id=object_id)
        if permissions is not None:
            query += """
        AND permission IN :permissions;"""
            placeholders["permissions"] = tuple(permissions)
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, placeholders)
            results = result.fetchall()
        permissions = defaultdict(set)
        for r in results:
            permissions[r['permission']].add(r['principal'])
        return permissions

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
