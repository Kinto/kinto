import os

import six
import structlog

from cliquet import utils


logger = structlog.get_logger()


class ClassicLogRenderer(object):
    """Classic log output for structlog.

    ::

        "GET   /v1/articles?_sort=title" 200 (3 ms) request.summary uid=234;

    """
    def __init__(self, settings):
        pass

    def __call__(self, logger, name, event_dict):
        if 'path' in event_dict:
            pattern = (u'"{method: <5} {path}{querystring}" {code} ({t} ms)'
                       ' {event} {context}')
        else:
            pattern = u'{event} {context}'

        output = {}
        for field in ['method', 'path', 'code', 't', 'event']:
            output[field] = event_dict.pop(field, '?')

        querystring = event_dict.pop('querystring', {})
        params = ['%s=%s' % qs for qs in querystring.items()]
        output['querystring'] = '?%s' % '&'.join(params) if params else ''

        context = ['%s=%s' % c for c in event_dict.items()]
        output['context'] = '; '.join(context)

        log_msg = pattern.format(**output)
        return log_msg


class MozillaHekaRenderer(object):
    """Build structured log entries as expected by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    """

    ENV_VERSION = '2.0'

    def __init__(self, settings):
        super(MozillaHekaRenderer, self).__init__()
        self.appname = settings['cliquet.project_name']
        self.hostname = utils.read_env('HOSTNAME', os.uname()[1])
        self.pid = os.getpid()

    def __call__(self, logger, name, event_dict):
        SYSLOG_LEVELS = {
            'critical': 0,
            'fatal': 0,
            'exception': 2,
            'error': 2,
            'warning': 4,
            'info': 6,
            'debug': 7,
        }
        severity = SYSLOG_LEVELS[name]

        MSEC_TO_NANOSEC = 1000000
        timestamp = utils.msec_time() * MSEC_TO_NANOSEC

        event = event_dict.pop('event', '')

        defaults = {
            'Timestamp': timestamp,
            'Logger': self.appname,
            'Type': event,
            'Hostname': self.hostname,
            'Severity': severity,
            'Pid': self.pid,
            'EnvVersion': self.ENV_VERSION,
            'Fields': {}
        }

        for f, v in defaults.items():
            event_dict.setdefault(f, v)

        fields = [k for k in event_dict.keys() if k not in defaults]
        for f in fields:
            value = event_dict.pop(f)

            # Heka relies on Protobuf, which doesn't support recursive objects.
            if isinstance(value, (dict)):
                value = utils.json.dumps(value)
            elif isinstance(value, (list, tuple)):
                if not all([isinstance(i, six.string_types) for i in value]):
                    value = utils.json.dumps(value)

            event_dict['Fields'][f] = value

        return utils.json.dumps(event_dict)
