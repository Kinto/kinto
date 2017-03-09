import logging

import colorama


def log_context(request, **kwargs):
    """Bind information to the current request summary log.
    """
    try:
        request._log_context.update(**kwargs)
    except AttributeError:
        request._log_context = kwargs
    return request._log_context


def decode_value(value):
    try:
        return str(value)
    except UnicodeDecodeError:  # pragma: no cover
        return bytes(value).decode('utf-8')


class ColorFormatter(logging.Formatter):
    EXCLUDED_LOGRECORD_ATTRS = set((
        'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
        'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
        'message', 'msg', 'name', 'pathname', 'process', 'processName',
        'relativeCreated', 'stack_info', 'thread', 'threadName'
    ))

    def format(self, record):
        RESET_ALL = colorama.Style.RESET_ALL
        BRIGHT = colorama.Style.BRIGHT
        CYAN = colorama.Fore.CYAN
        MAGENTA = colorama.Fore.MAGENTA
        YELLOW = colorama.Fore.YELLOW

        event_dict = {**record.__dict__}

        if 'path' in event_dict:
            pattern = (BRIGHT +
                       '"{method: <5} {path}{querystring}"' +
                       RESET_ALL +
                       YELLOW + ' {code} ({t} ms)' +
                       RESET_ALL +
                       ' {event} {context}')
        else:
            pattern = BRIGHT + '{event}' + RESET_ALL + ' {context}'

        output = {
            'event': str(event_dict.pop('msg', '?')).format(**event_dict)
        }
        for field in ['method', 'path', 'code', 't']:
            output[field] = decode_value(event_dict.pop(field, '?'))

        querystring = event_dict.pop('querystring', {})
        params = [decode_value('{}={}'.format(*qs)) for qs in querystring.items()]
        output['querystring'] = '?{}'.format('&'.join(params) if params else '')

        output['context'] = " ".join(
            CYAN + key + RESET_ALL +
            "=" +
            MAGENTA + decode_value(event_dict[key]) +
            RESET_ALL
            for key in sorted([k for k in event_dict.keys()
                               if k not in self.EXCLUDED_LOGRECORD_ATTRS])
        )

        log_msg = pattern.format_map(output)
        return log_msg
