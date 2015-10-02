from __future__ import absolute_import

import os

from collections import defaultdict
from six.moves.urllib import parse as urlparse

from cliquet import logger
from cliquet.permission import PermissionBase
from cliquet.storage.postgresql import PostgreSQLClient


class PostgreSQL(PostgreSQLClient, PermissionBase):
    """Permission backend using PostgreSQL.

    Enable in configuration::

        cliquet.permission_backend = cliquet.permission.postgresql

    Database location URI can be customized::

        cliquet.permission_url = postgres://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in :file:`~/.pgpass` (*see PostgreSQL documentation*).

    .. note::

        Some tables and indices are created when ``cliquet migrate`` is run.
        This requires some privileges on the database, or some error will
        be raised.

        **Alternatively**, the schema can be initialized outside the
        python application, using the SQL file located in
        :file:`cliquet/permission/postgresql/schema.sql`. This allows to
        distinguish schema manipulation privileges from schema usage.


    A threaded connection pool is enabled by default::

        cliquet.permission_pool_size = 10

    .. note::

        Using a `dedicated connection pool <http://pgpool.net>`_ is still
        recommended to allow load balancing, replication or limit the number
        of connections used in a multi-process deployment.

    :noindex:
    """

    def __init__(self, **kwargs):
        super(PostgreSQL, self).__init__(**kwargs)

    def initialize_schema(self):
        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, 'schema.sql')).read()
        with self.connect() as cursor:
            cursor.execute(schema)
        logger.info('Created PostgreSQL permission tables')

    def flush(self):
        query = """
        DELETE FROM user_principals;
        DELETE FROM access_control_entries;
        """
        with self.connect() as cursor:
            cursor.execute(query)
        logger.debug('Flushed PostgreSQL permission tables')

    def add_user_principal(self, user_id, principal):
        query = """
        INSERT INTO user_principals (user_id, principal)
        SELECT %(user_id)s, %(principal)s
         WHERE NOT EXISTS (
            SELECT principal
            FROM user_principals
            WHERE user_id = %(user_id)s
              AND principal = %(principal)s
        );"""
        with self.connect() as cursor:
            cursor.execute(query, dict(user_id=user_id, principal=principal))

    def remove_user_principal(self, user_id, principal):
        query = """
        DELETE FROM user_principals
         WHERE user_id = %(user_id)s
           AND principal = %(principal)s;"""
        with self.connect() as cursor:
            cursor.execute(query, dict(user_id=user_id, principal=principal))

    def user_principals(self, user_id):
        query = """
        SELECT principal
          FROM user_principals
         WHERE user_id = %(user_id)s;"""
        with self.connect() as cursor:
            cursor.execute(query, dict(user_id=user_id))
            results = cursor.fetchall()
        return set([r['principal'] for r in results])

    def add_principal_to_ace(self, object_id, permission, principal):
        query = """
        INSERT INTO access_control_entries (object_id, permission, principal)
        SELECT %(object_id)s, %(permission)s, %(principal)s
         WHERE NOT EXISTS (
            SELECT principal
              FROM access_control_entries
             WHERE object_id = %(object_id)s
               AND permission = %(permission)s
               AND principal = %(principal)s
        );"""
        with self.connect() as cursor:
            cursor.execute(query, dict(object_id=object_id,
                                       permission=permission,
                                       principal=principal))

    def remove_principal_from_ace(self, object_id, permission, principal):
        query = """
        DELETE FROM access_control_entries
         WHERE object_id = %(object_id)s
           AND permission = %(permission)s
           AND principal = %(principal)s;"""
        with self.connect() as cursor:
            cursor.execute(query, dict(object_id=object_id,
                                       permission=permission,
                                       principal=principal))

    def object_permission_principals(self, object_id, permission):
        query = """
        SELECT principal
          FROM access_control_entries
         WHERE object_id = %(object_id)s
           AND permission = %(permission)s;"""
        with self.connect() as cursor:
            cursor.execute(query, dict(object_id=object_id,
                                       permission=permission))
            results = cursor.fetchall()
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
        with self.connect() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
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

        with self.connect() as cursor:
            cursor.execute(query, placeholders)
            results = cursor.fetchall()
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

        with self.connect() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
        return result['matched'] > 0

    def object_permissions(self, object_id, permissions=None):
        query = """
        SELECT permission, principal
        FROM access_control_entries
        WHERE object_id = %(object_id)s"""

        placeholders = dict(object_id=object_id)
        if permissions is not None:
            query += """
        AND permission IN %(permissions)s;"""
            placeholders["permissions"] = tuple(permissions)
        with self.connect() as cursor:
            cursor.execute(query, placeholders)
            results = cursor.fetchall()
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
            specified_perms.append("(%%(perm_%s)s)" % i)
            for principal in principals:
                j = len(new_perms)
                placeholders['principal_%s' % j] = principal
                new_perms.append("(%%(perm_%s)s, %%(principal_%s)s)" % (i, j))

        delete_query = """
        WITH specified_perms AS (
          VALUES %(specified_perms)s
        )
        DELETE FROM access_control_entries
         USING specified_perms
         WHERE object_id = %%(object_id)s AND permission = column1
        """ % dict(specified_perms=','.join(specified_perms))

        insert_query = """
        WITH new_aces AS (
          VALUES %(new_perms)s
        )
        INSERT INTO access_control_entries(object_id, permission, principal)
          SELECT %%(object_id)s, column1, column2
            FROM new_aces;
        """ % dict(new_perms=','.join(new_perms))

        with self.connect() as cursor:
            cursor.execute(delete_query, placeholders)
            cursor.execute(insert_query, placeholders)

    def delete_object_permissions(self, *object_id_list):
        query = """
        DELETE FROM access_control_entries
         WHERE object_id IN %(object_id_list)s;"""
        with self.connect() as cursor:
            cursor.execute(query, dict(object_id_list=tuple(object_id_list)))


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['permission_url']
    uri = urlparse.urlparse(uri)
    pool_size = int(settings['permission_pool_size'])

    conn_kwargs = dict(pool_size=pool_size,
                       host=uri.hostname,
                       port=uri.port,
                       user=uri.username,
                       password=uri.password,
                       database=uri.path[1:] if uri.path else '')
    # Filter specified values only, to preserve PostgreSQL defaults
    conn_kwargs = dict([(k, v) for k, v in conn_kwargs.items() if v])

    return PostgreSQL(**conn_kwargs)
