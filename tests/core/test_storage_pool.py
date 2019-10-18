import threading
import time
import unittest

from pyramid import testing

from kinto.core.testing import skip_if_no_postgresql


@skip_if_no_postgresql
class QueuePoolWithMaxBacklogTest(unittest.TestCase):
    def setUp(self):
        from kinto.core.storage.postgresql.client import create_from_config

        self.connections = []
        self.errors = []

        config = testing.setUp(
            settings={
                "pooltest_url": "sqlite:///:memory:",
                "pooltest_pool_size": 2,
                "pooltest_pool_timeout": 1,
                "pooltest_max_backlog": 2,
                "pooltest_max_overflow": 1,
            }
        )
        # Create an engine with known pool parameters.
        # Use create_from_config() to make sure it is used by default
        # and handles parameters.
        client = create_from_config(config, prefix="pooltest_")
        session = client.session_factory()
        self.engine = session.get_bind()

    def take_connection(self):
        try:
            self.connections.append(self.engine.connect())
        except Exception as e:
            self.errors.append(e)

    def exhaust_pool(self):
        # The size of the pool is two, so we can take
        # two connections right away without any error.
        self.take_connection()
        self.take_connection()
        # The pool allows an overflow of 1, so we can
        # take another, ephemeral connection without any error.
        self.take_connection()
        self.assertEqual(len(self.connections), 3)
        self.assertEqual(len(self.errors), 0)

    def test_max_backlog_fails_when_reached(self):
        self.exhaust_pool()

        # The pool allows a backlog of 2, so we can
        # spawn two threads that will block waiting for a connection.
        thread1 = threading.Thread(target=self.take_connection)
        thread1.start()
        thread2 = threading.Thread(target=self.take_connection)
        thread2.start()
        self.assertEqual(len(self.connections), 3)
        self.assertEqual(len(self.errors), 0)
        # The pool is now exhausted and at maximum backlog.
        # Trying to take another connection fails immediately.
        t1 = time.time()
        self.take_connection()
        t2 = time.time()
        self.assertEqual(len(self.connections), 3)
        # This checks that it failed immediately rather than timing out.
        self.assertTrue(t2 - t1 < 1.1)
        self.assertTrue(len(self.errors) >= 1)

        # And eventually, the blocked threads will time out.
        thread1.join()
        thread2.join()
        self.assertEqual(len(self.connections), 3)
        self.assertEqual(len(self.errors), 3)

    def test_recreates_reinstantiate_with_same_pool_class(self):
        from kinto.core.storage.postgresql.pool import QueuePoolWithMaxBacklog

        pool = QueuePoolWithMaxBacklog(None, max_backlog=2, pool_size=2)
        other = pool.recreate()
        self.assertEqual(pool._pool.__class__, other._pool.__class__)
        self.assertEqual(other._pool.max_backlog, 2)

    def test_has_pool_size_of_25_by_default(self):
        from kinto.core.storage.postgresql.pool import QueuePoolWithMaxBacklog

        pool = QueuePoolWithMaxBacklog(creator=None)
        self.assertEqual(pool.size(), 25)
