from functools import wraps
import statsd as statsd_module


def noop(f):
    """Decorator calling the decorated function"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


class Client(object):
    statsd = None

    @classmethod
    def setup_client(cls, settings):
        if settings['cliquet.statsd_endpoint'] is not None:
            host, port = settings['cliquet.statsd_endpoint'].split(':')
            cls.statsd = statsd_module.StatsClient(host, port)

    @classmethod
    def timer(cls, key):
        if cls.statsd:
            return cls.statsd.timer(key)
        return noop

    @classmethod
    def incr(cls, key):
        if cls.statsd:
            return cls.statsd.incr(key)


def get_metaclass(prefix):
    """Returns a Metaclass decorating all public methods with a statsd timer.
    """
    class StatsdTimer(type):

        def __new__(cls, name, bases, members):
            attrs = {}
            for key, value in members.items():
                if not key.startswith('_') and hasattr(value, '__call__'):
                    statsd_key = "%s.%s.%s" % (prefix, name.lower(), key)
                    attrs[key] = Client.timer(statsd_key)(value)
                else:
                    attrs[key] = value

            return type.__new__(cls, name, bases, attrs)

    return StatsdTimer

StorageTimer = get_metaclass('storage')
CacheTimer = get_metaclass('cache')
setup_client = Client.setup_client
