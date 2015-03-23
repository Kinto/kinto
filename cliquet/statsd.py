from __future__ import absolute_import

try:
    import statsd as statsd_module
except ImportError:
    pass  # NOQA
from six.moves.urllib import parse as urlparse

from cliquet import utils


class Client(object):
    def __init__(self, host, port):
        self._client = statsd_module.StatsClient(host, port)

    def watch_execution_time(self, obj, prefix=''):
        classname = utils.classname(obj)
        members = dir(obj)
        for name in members:
            value = getattr(obj, name)
            if not name.startswith('_') and hasattr(value, '__call__'):
                statsd_key = "%s.%s.%s" % (prefix, classname, name)
                decorated_method = self.timer(statsd_key)(value)
                setattr(obj, name, decorated_method)

    def timer(self, key):
        return self._client.timer(key)


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['cliquet.statsd_url']
    uri = urlparse.urlparse(uri)

    return Client(uri.hostname, uri.port)
