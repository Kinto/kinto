from __future__ import absolute_import

import os

from kinto.core import logger
from kinto.core.cache import CacheBase
from kinto.core.storage.postgresql.client import create_from_config
from kinto.core.utils import json


class Cache(CacheBase):
    """Cache backend using PostgreSQL.

    Enable in configuration::

        kinto.cache_backend = kinto.core.cache.postgresql

    Database location URI can be customized::

        kinto.cache_url = postgres://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in :file:`~/.pgpass` (*see PostgreSQL documentation*).

    .. note::

        Some tables and indices are created when ``kinto migrate`` is run.
        This requires some privileges on the database, or some error will
        be raised.

        **Alternatively**, the schema can be initialized outside the
        python application, using the SQL file located in
        :file:`kinto/core/cache/postgresql/schema.sql`. This allows to
        distinguish schema manipulation privileges from schema usage.


    A connection pool is enabled by default::

        kinto.cache_pool_size = 10
        kinto.cache_maxoverflow = 10
        kinto.cache_max_backlog = -1
        kinto.cache_pool_recycle = -1
        kinto.cache_pool_timeout = 30
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
        super(Cache, self).__init__(*args, **kwargs)
        self.client = client

    def initialize_schema(self):
        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, 'schema.sql')).read()
        # Since called outside request, force commit.
        with self.client.connect(force_commit=True) as conn:
            conn.execute(schema)
        logger.info('Created PostgreSQL cache tables')

    def flush(self):
        query = """
        DELETE FROM cache;
        """
        # Since called outside request (e.g. tests), force commit.
        with self.client.connect(force_commit=True) as conn:
            conn.execute(query)
        logger.debug('Flushed PostgreSQL cache tables')

    def ttl(self, key):
        query = """
        SELECT EXTRACT(SECOND FROM (ttl - now())) AS ttl
          FROM cache
         WHERE key = :key
           AND ttl IS NOT NULL;
        """
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query, dict(key=self.prefix + key))
            if result.rowcount > 0:
                return result.fetchone()['ttl']
        return -1

    def expire(self, key, ttl):
        query = """
        UPDATE cache SET ttl = sec2ttl(:ttl) WHERE key = :key;
        """
        with self.client.connect() as conn:
            conn.execute(query, dict(ttl=ttl, key=self.prefix + key))

    def set(self, key, value, ttl=None):
        query = """
        WITH upsert AS (
            UPDATE cache SET value = :value, ttl = sec2ttl(:ttl)
             WHERE key=:key
            RETURNING *)
        INSERT INTO cache (key, value, ttl)
        SELECT :key, :value, sec2ttl(:ttl)
        WHERE NOT EXISTS (SELECT * FROM upsert)
        """
        value = json.dumps(value)
        with self.client.connect() as conn:
            conn.execute(query, dict(key=self.prefix + key,
                                     value=value, ttl=ttl))

    def get(self, key):
        purge = "DELETE FROM cache WHERE ttl IS NOT NULL AND now() > ttl;"
        query = "SELECT value FROM cache WHERE key = :key;"
        with self.client.connect() as conn:
            conn.execute(purge)
            result = conn.execute(query, dict(key=self.prefix + key))
            if result.rowcount > 0:
                value = result.fetchone()['value']
                return json.loads(value)

    def delete(self, key):
        query = "DELETE FROM cache WHERE key = :key"
        with self.client.connect() as conn:
            conn.execute(query, dict(key=self.prefix + key))


def load_from_config(config):
    settings = config.get_settings()
    client = create_from_config(config, prefix='cache_')
    return Cache(client=client, cache_prefix=settings['cache_prefix'])
