from __future__ import absolute_import
import types

try:
    import statsd as statsd_module
except ImportError:  # pragma: no cover
    statsd_module = None

from six.moves.urllib import parse as urlparse

from cliquet import utils


class Client(object):
    def __init__(self, host, port, prefix):
        self._client = statsd_module.StatsClient(host, port, prefix=prefix)

    def watch_execution_time(self, obj, prefix='', classname=None):
        classname = classname or utils.classname(obj)
        members = dir(obj)
        for name in members:
            value = getattr(obj, name)
            is_method = isinstance(value, types.MethodType)
            if not name.startswith('_') and is_method:
                statsd_key = "%s.%s.%s" % (prefix, classname, name)
                decorated_method = self.timer(statsd_key)(value)
                setattr(obj, name, decorated_method)

    def timer(self, key):
        return self._client.timer(key)

    def count(self, key, unique=None):
        if unique is None:
            return self._client.incr(key, count=1)
        else:
            return self._client.set(key, unique)


def statsd_count(request, count_key):
    statsd = request.registry.statsd
    if statsd:
        statsd.count(count_key)


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['statsd_url']
    uri = urlparse.urlparse(uri)

    if settings['project_name'] != '':
        prefix = settings['project_name']
    else:
        prefix = settings['statsd_prefix']

    return Client(uri.hostname, uri.port, prefix)
