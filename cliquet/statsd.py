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
    global statsd
    if statsd:
        return statsd.timer(key_name)
    return dummy_decorator


def incr(key_name):
    global statsd
    if statsd:
        return statsd.incr(key_name)
