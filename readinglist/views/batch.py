import json
import colander
import six

from cornice import Service
from pyramid.request import Request
from pyramid import httpexceptions
from six.moves.urllib import parse as urlparse

from readinglist import logger
from readinglist import errors
from readinglist.utils import merge_dicts


valid_http_method = colander.OneOf(('GET', 'HEAD', 'DELETE', 'TRACE',
                                    'POST', 'PUT', 'PATCH'))


def string_values(node, cstruct):
    """Validate that a ``colander.Mapping`` only has strings in its values.

    :warning:

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

    def deserialize(self, cstruct=colander.null):
        """Preprocess received data to merge defaults."""
        if cstruct is colander.null:
            return colander.null

        # On defaults, path is not mandatory.
        self.get('defaults').get('path').missing = colander.drop

        # Fill requests values with defaults.
        requests = cstruct.get('requests', [])
        for request in requests:
            defaults = cstruct.get('defaults')
            if isinstance(defaults, dict):
                merge_dicts(request, defaults)

        return super(BatchPayloadSchema, self).deserialize(cstruct)


batch = Service(name="batch", path='/batch',
                description="Batch operations",
                error_handler=errors.json_error)


@batch.post(schema=BatchPayloadSchema)
def post_batch(request):
    requests = request.validated['requests']

    limit = request.registry.settings.get('readinglist.batch_max_requests')
    if limit and len(requests) > limit:
        error_msg = 'Number of requests is limited to %s' % limit
        request.errors.add('body', 'requests', error_msg)
        return

    if any([batch.path in req['path'] for req in requests]):
        error_msg = 'Recursive call on %s endpoint is forbidden.' % batch.path
        request.errors.add('body', 'requests', error_msg)
        return

    responses = []

    for subrequest_spec in requests:
        subrequest = build_request(request, subrequest_spec)

        try:
            subresponse = request.invoke_subrequest(subrequest)
        except httpexceptions.HTTPException as e:
            subresponse = e
        except Exception as e:
            logger.exception(e)
            subresponse = errors.HTTPInternalServerError()

        subresponse = build_response(subresponse, subrequest)
        responses.append(subresponse)

    return {
        'responses': responses
    }


def build_request(original, dict_obj):
    """
    Transform a dict object into a ``pyramid.request.Request`` object.

    :param original: the original batch request.
    :param dict_obj: a dict object with the sub-request specifications.
    """
    path = dict_obj['path']
    path = urlparse.quote(path.encode('utf8'))

    method = dict_obj.get('method') or 'GET'
    headers = dict(original.headers)
    headers.update(**dict_obj.get('headers') or {})
    payload = dict_obj.get('body') or None

    # Payload is always a dict (from ``BatchRequestSchema.body``).
    # Send it as JSON for subrequests.
    if isinstance(payload, dict):
        headers['Content-Type'] = 'application/json; charset=utf-8'
        payload = json.dumps(payload)

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
    dict_obj['path'] = request.path
    dict_obj['status'] = response.status_code
    dict_obj['headers'] = dict(response.headers)

    body = ''
    if request.method != 'HEAD':
        # XXX : Pyramid should not have built response body!
        try:
            body = response.json
        except ValueError:
            body = response.body
    dict_obj['body'] = body

    return dict_obj
