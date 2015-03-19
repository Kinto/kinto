from functools import wraps
import statsd as statsd_module


def dummy_decorator(f):
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
    return dummy_decorator


def incr(key_name):
    if statsd:
        return statsd.incr(key_name)


def getStatsdTimer(prefix):
    class StatsdTimer(type):
        """Decorate all methods with a statsd timer."""

        def __new__(cls, name, bases, members):
            attrs = {}
            for key, value in members.items():
                if not key.startswith('_') and hasattr(value, '__call__'):
                    attrs[key] = timer("%s.%s.%s" % (prefix,
                                                     name.lower(), key))(value)
                else:
                    attrs[key] = value

            return type.__new__(cls, name, bases, attrs)

    return StatsdTimer

StorageStatsdTimer = getStatsdTimer('storage')
CacheStatsdTimer = getStatsdTimer('cache')
