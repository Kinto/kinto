from sqlalchemy.util.queue import Queue
from sqlalchemy.pool import QueuePool


class _QueueWithMaxBacklog(Queue):
    """SQLAlchemy Queue subclass with a limit on the length of the backlog.

    This base Queue class sets no limit on the number of threads that can be
    simultaneously blocked waiting for an item on the queue.  This class
    adds a "max_backlog" parameter that can be used to bound this number.
    """

    def __init__(self, maxsize=0, max_backlog=-1):
        self.max_backlog = max_backlog
        self.cur_backlog = 0
        Queue.__init__(self, maxsize)

    def get(self, block=True, timeout=None):
        # The SQLAlchemy Queue class uses a re-entrant mutext by default,
        # so it's safe to acquire it both here and in the superclass method.
        with self.mutex:
            self.cur_backlog += 1
            try:
                if self.max_backlog >= 0:
                    if self.cur_backlog > self.max_backlog:
                        block = False
                        timeout = None
                return Queue.get(self, block, timeout)
            finally:
                self.cur_backlog -= 1


class QueuePoolWithMaxBacklog(QueuePool):
    """An SQLAlchemy QueuePool with a limit on the length of the backlog.

    The base QueuePool class sets no limit on the number of threads that can
    be simultaneously attempting to connect to the database.  This means that
    a misbehaving database can easily lock up all threads by keeping them
    waiting in the queue.

    This QueuePool subclass provides a "max_backlog" that limits the number
    of threads that can be in the queue waiting for a connection.  Once this
    limit has been reached, any further attempts to acquire a connection will
    be rejected immediately.
    """

    def __init__(self, creator, max_backlog=-1, **kwds):
        QueuePool.__init__(self, creator, **kwds)
        self._pool = _QueueWithMaxBacklog(self._pool.maxsize, max_backlog)

    def recreate(self):
        new_self = QueuePool.recreate(self)
        new_self._pool = _QueueWithMaxBacklog(self._pool.maxsize,
                                              self._pool.max_backlog)
        return new_self
