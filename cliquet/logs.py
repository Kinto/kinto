import os
from datetime import datetime

import structlog
from pyramid.events import NewRequest, NewResponse

from cliquet import utils


logger = structlog.get_logger()


def setup_logging(config):
    """Setup structured logging, and emit `request.summary` event on each
    request, as recommanded by Mozilla Services standard:

    * https://mana.mozilla.org/wiki/display/CLOUDSERVICES/Logging+Standard
    * http://12factor.net/logs
    """
    settings = config.get_settings()

    renderer_klass = config.maybe_dotted(settings['cliquet.logging_renderer'])
    renderer = renderer_klass(settings)

    structlog.configure(
        # Share the logger context by thread.
        context_class=structlog.threadlocal.wrap_dict(dict),
        # Integrate with Pyramid logging facilities.
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # Setup logger output format.
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.format_exc_info,
            renderer,
        ])

    def on_new_request(event):
        request = event.request
        # Save the time the request was received by the server.
        event.request._received_at = utils.msec_time()

        # New logger context, with infos for request summary logger.
        logger.new(agent=request.headers.get('User-Agent'),
                   path=event.request.path,
                   method=request.method,
                   querystring=dict(request.GET),
                   uid=request.authenticated_userid,
                   lang=request.headers.get('Accept-Language'),
                   errno=None)

    config.add_subscriber(on_new_request, NewRequest)

    def on_new_response(event):
        response = event.response
        request = event.request

        # Compute the request processing time in msec (-1 if unknown)
        current = utils.msec_time()
        duration = current - getattr(request, '_received_at', current - 1)
        isotimestamp = datetime.fromtimestamp(current/1000).isoformat()

        # Bind infos for request summary logger.
        logger.bind(time=isotimestamp,
                    code=response.status_code,
                    t=duration)

        # Ouput application request summary.
        logger.info('request.summary')

    config.add_subscriber(on_new_response, NewResponse)


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
            event_dict['Fields'][f] = event_dict.pop(f)

        return utils.json.dumps(event_dict)
