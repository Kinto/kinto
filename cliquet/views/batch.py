import colander
import six

from pyramid.request import Request
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid import httpexceptions
from six.moves.urllib import parse as urlparse

from cliquet import errors
from cliquet import logger
from cliquet import Service
from cliquet.utils import json, merge_dicts


valid_http_method = colander.OneOf(('GET', 'HEAD', 'DELETE', 'TRACE',
                                    'POST', 'PUT', 'PATCH'))


def string_values(node, cstruct):
    """Validate that a ``colander.Mapping`` only has strings in its values.

    .. warning::

        Should be associated to a ``colander.Mapping`` schema node.
    """
    are_strings = [isinstance(v, six.string_types) for v in cstruct.values()]
    if not all(are_strings):
        error_msg = '%s contains non string value' % cstruct
        raise colander.Invalid(node, error_msg)


class BatchRequestSchema(colander.MappingSchema):
    method = colander.SchemaNode(colander.String(),
                                 validator=valid_http_method,
                                 missing=colander.drop)
    path = colander.SchemaNode(colander.String(),
                               validator=colander.Regex('^/'))
    headers = colander.SchemaNode(colander.Mapping(unknown='preserve'),
                                  validator=string_values,
                                  missing=colander.drop)
    body = colander.SchemaNode(colander.Mapping(unknown='preserve'),
                               missing=colander.drop)


class BatchPayloadSchema(colander.MappingSchema):
    defaults = BatchRequestSchema(missing=colander.drop).clone()
    requests = colander.SchemaNode(colander.Sequence(),
                                   BatchRequestSchema())

    def unflatten(self, data):
        """Preprocess received data to merge defaults.

        Override schema unflattening to plug into Cornice schema validation.
        This is the only method that Cornice calls at the schema level before
        iterating on each field to deserialize them.
        """
        # On defaults, path is not mandatory.
        self.get('defaults').get('path').missing = colander.drop

        # Fill requests values with defaults.
        requests = data.get('requests', [])
        for request in requests:
            defaults = data.get('defaults')
            if isinstance(defaults, dict):
                merge_dicts(request, defaults)

        return data


batch = Service(name="batch", path='/batch',
                description="Batch operations",
                error_handler=errors.json_error_handler)


@batch.post(schema=BatchPayloadSchema, permission=NO_PERMISSION_REQUIRED)
def post_batch(request):
    requests = request.validated['requests']
    batch_size = len(requests)

    limit = request.registry.settings['cliquet.batch_max_requests']
    if limit and len(requests) > int(limit):
        error_msg = 'Number of requests is limited to %s' % limit
        request.errors.add('body', 'requests', error_msg)
        return

    if any([batch.path in req['path'] for req in requests]):
        error_msg = 'Recursive call on %s endpoint is forbidden.' % batch.path
        request.errors.add('body', 'requests', error_msg)
        return

    responses = []

    sublogger = logger.new()

    for subrequest_spec in requests:
        subrequest = build_request(request, subrequest_spec)

        sublogger.bind(path=subrequest.path,
                       method=subrequest.method)

        try:
            subresponse = request.invoke_subrequest(subrequest)

        except httpexceptions.HTTPException as e:
            error_msg = 'Failed batch subrequest'
            subresponse = errors.http_error(e, message=error_msg)
        except Exception as e:
            logger.error(e)
            subresponse = errors.http_error(
                httpexceptions.HTTPInternalServerError())

        sublogger.bind(code=subresponse.status_code)
        sublogger.info('subrequest.summary')

        subresponse = build_response(subresponse, subrequest)
        responses.append(subresponse)

    # Rebing batch request for summary
    logger.bind(path=batch.path,
                method=request.method,
                batch_size=batch_size,
                agent=request.headers.get('User-Agent'),)

    return {
        'responses': responses
    }


def build_request(original, dict_obj):
    """
    Transform a dict object into a ``pyramid.request.Request`` object.

    :param original: the original batch request.
    :param dict_obj: a dict object with the sub-request specifications.
    """
    api_prefix = '/%s' % original.upath_info.split('/')[1]
    path = dict_obj['path']
    if not path.startswith(api_prefix):
        path = api_prefix + path

    path = path.encode('utf-8')

    method = dict_obj.get('method') or 'GET'
    headers = dict(original.headers)
    headers.update(**dict_obj.get('headers') or {})
    payload = dict_obj.get('body') or ''

    # Payload is always a dict (from ``BatchRequestSchema.body``).
    # Send it as JSON for subrequests.
    if isinstance(payload, dict):
        headers['Content-Type'] = 'application/json; charset=utf-8'
        payload = json.dumps(payload)

    if six.PY3:  # pragma: no cover
        path = path.decode('latin-1')

    request = Request.blank(path=path,
                            headers=headers,
                            POST=payload,
                            method=method)

    return request


def build_response(response, request):
    """
    Transform a ``pyramid.response.Response`` object into a serializable dict.

    :param response: a response object, returned by Pyramid.
    :param request: the request that was used to get the response.
    """
    dict_obj = {}
    dict_obj['path'] = urlparse.unquote(request.path)
    dict_obj['status'] = response.status_code
    dict_obj['headers'] = dict(response.headers)

    body = ''
    if request.method != 'HEAD':
        # XXX : Pyramid should not have built response body for HEAD!
        try:
            body = response.json
        except ValueError:
            body = response.body
    dict_obj['body'] = body

    return dict_obj
