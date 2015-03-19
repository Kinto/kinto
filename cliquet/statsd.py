from functools import wraps
import statsd as statsd_module


def noop(f):
    """Just call the given function."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


statsd = None


def setup_client(settings):
    global statsd
    if settings['cliquet.statsd_endpoint'] is not None:
        host, port = settings['cliquet.statsd_endpoint'].split(':')
        statsd = statsd_module.StatsClient(host, port)


def timer(key_name):
    if statsd:
        return statsd.timer(key_name)
    return noop


def incr(key_name):
    if statsd:
        return statsd.incr(key_name)


def get_statsd_timer(prefix):
    """Returns a Metaclass decorating all public methods with a statsd timer.
    """
    class StatsdTimer(type):

        def __new__(cls, name, bases, members):
            attrs = {}
            for key, value in members.items():
                if not key.startswith('_') and hasattr(value, '__call__'):
                    statsd_key = "%s.%s.%s" % (prefix, name.lower(), key)
                    attrs[key] = timer(statsd_key)(value)
                else:
                    attrs[key] = value

            return type.__new__(cls, name, bases, attrs)

    return StatsdTimer

StorageTimer = get_statsd_timer('storage')
CacheTimer = get_statsd_timer('cache')
