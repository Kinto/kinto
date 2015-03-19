from functools import wraps
import statsd


def dummy_decorator(f):
    """Just call the given function."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


class StatsdClient(object):
    """This act as a proxy for statsd calls."""
    statsd = None

    @classmethod
    def setup_client(cls, settings):
        if settings['cliquet.statsd_endpoint'] is not None:
            host, port = settings['cliquet.statsd_endpoint'].split(':')
            cls.statsd = statsd.StatsClient(host, port)

    @classmethod
    def timer(cls, key_name):
        if cls.statsd:
            return cls.statsd.timer(key_name)
        return dummy_decorator

    @classmethod
    def incr(cls, key_name):
        if cls.statsd:
            return cls.statsd.incr(key_name)
