from __future__ import absolute_import
from functools import wraps

import os
import time

from kinto.core import logger
from kinto.core.cache import CacheBase
from kinto.core.storage.postgresql.client import create_from_config
from kinto.core.storage.exceptions import BackendError
from kinto.core.utils import json


DELAY_BETWEEN_RETRIES_IN_SECONDS = 0.005
MAX_RETRIES = 10


def retry_on_failure(func):
    @wraps(func)
    def wraps_func(self, *args, **kwargs):
        tries = kwargs.pop('tries', 0)
        try:
            return func(self, *args, **kwargs)
        except BackendError as e:
            if tries < MAX_RETRIES:
                # Skip delay the 2 first times.
                delay = max(0, tries - 1) * DELAY_BETWEEN_RETRIES_IN_SECONDS
                time.sleep(delay)
                return wraps_func(self, tries=(tries + 1), *args, **kwargs)
            raise e
    return wraps_func


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
        super(Cache, self).__init__(*args, **kwargs)
        self.client = client

    def initialize_schema(self, dry_run=False):
        # Check if cache table exists.
        query = """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'cache';
        """
        with self.client.connect(readonly=True) as conn:
            result = conn.execute(query)
            if result.rowcount > 0:
                logger.info("PostgreSQL cache schema is up-to-date.")
                return

        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        sql_file = os.path.join(here, 'schema.sql')

        if dry_run:
            logger.info("Create cache schema from %s" % sql_file)
            return

        # Since called outside request, force commit.
        schema = open(sql_file).read()
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

    @retry_on_failure
    def set(self, key, value, ttl=None):
        if ttl is None:
            logger.warning("No TTL for cache key %r" % key)
        query = """
        INSERT INTO cache (key, value, ttl)
        VALUES (:key, :value, sec2ttl(:ttl))
        ON CONFLICT (key) DO UPDATE
        SET value = :value,
            ttl = sec2ttl(:ttl);
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
    client = create_from_config(config, prefix='cache_', with_transaction=False)
    return Cache(client=client, cache_prefix=settings['cache_prefix'])
