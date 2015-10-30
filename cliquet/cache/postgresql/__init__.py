from __future__ import absolute_import

import os

from cliquet import logger
from cliquet.cache import CacheBase
from cliquet.storage.postgresql.client import create_from_config
from cliquet.utils import json


class Cache(CacheBase):
    """Cache backend using PostgreSQL.

    Enable in configuration::

        cliquet.cache_backend = cliquet.cache.postgresql

    Database location URI can be customized::

        cliquet.cache_url = postgres://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in :file:`~/.pgpass` (*see PostgreSQL documentation*).

    .. note::

        Some tables and indices are created when ``cliquet migrate`` is run.
        This requires some privileges on the database, or some error will
        be raised.

        **Alternatively**, the schema can be initialized outside the
        python application, using the SQL file located in
        :file:`cliquet/cache/postgresql/schema.sql`. This allows to
        distinguish schema manipulation privileges from schema usage.


    A threaded connection pool is enabled by default::

        cliquet.cache_pool_size = 10

    .. note::

        Using a `dedicated connection pool <http://pgpool.net>`_ is still
        recommended to allow load balancing, replication or limit the number
        of connections used in a multi-process deployment.

    :noindex:
    """
    def __init__(self, client, *args, **kwargs):
        super(Cache, self).__init__(*args, **kwargs)
        self.client = client

    def initialize_schema(self):
        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, 'schema.sql')).read()
        with self.client.connect() as cursor:
            cursor.execute(schema)
        logger.info('Created PostgreSQL cache tables')

    def flush(self):
        query = """
        DELETE FROM cache;
        """
        with self.client.connect() as cursor:
            cursor.execute(query)
        logger.debug('Flushed PostgreSQL cache tables')

    def ttl(self, key):
        query = """
        SELECT EXTRACT(SECOND FROM (ttl - now())) AS ttl
          FROM cache
         WHERE key = %s
           AND ttl IS NOT NULL;
        """
        with self.client.connect() as cursor:
            cursor.execute(query, (key,))
            if cursor.rowcount > 0:
                return cursor.fetchone()['ttl']
        return -1

    def expire(self, key, ttl):
        query = """
        UPDATE cache SET ttl = sec2ttl(%s) WHERE key = %s;
        """
        with self.client.connect() as cursor:
            cursor.execute(query, (ttl, key,))

    def set(self, key, value, ttl=None):
        query = """
        WITH upsert AS (
            UPDATE cache SET value = %(value)s, ttl = sec2ttl(%(ttl)s)
             WHERE key=%(key)s
            RETURNING *)
        INSERT INTO cache (key, value, ttl)
        SELECT %(key)s, %(value)s, sec2ttl(%(ttl)s)
        WHERE NOT EXISTS (SELECT * FROM upsert)
        """
        value = json.dumps(value)
        with self.client.connect() as cursor:
            cursor.execute(query, dict(key=key, value=value, ttl=ttl))

    def get(self, key):
        purge = "DELETE FROM cache WHERE ttl IS NOT NULL AND now() > ttl;"
        query = "SELECT value FROM cache WHERE key = %s;"
        with self.client.connect() as cursor:
            cursor.execute(purge)
            cursor.execute(query, (key,))
            if cursor.rowcount > 0:
                value = cursor.fetchone()['value']
                return json.loads(value)

    def delete(self, key):
        query = "DELETE FROM cache WHERE key = %s"
        with self.client.connect() as cursor:
            cursor.execute(query, (key,))


def load_from_config(config):
    client = create_from_config(config, prefix='cache_')
    return Cache(client=client)
