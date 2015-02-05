import colander
from cornice import Service
from pyramid.request import Request
from pyramid import httpexceptions
import six

from readinglist import logger
from readinglist.errors import HTTPInternalServerError


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
    body = colander.SchemaNode(colander.String(),
                               missing=colander.drop)


class BatchPayloadSchema(colander.MappingSchema):
    requests = colander.SchemaNode(colander.Sequence(),
                                   BatchRequestSchema())


batch = Service(name="batch", path='/batch',
                description="Batch operations")


@batch.post(permission='readonly', schema=BatchPayloadSchema)
def post_batch(request):
    responses = []

    for subrequest_spec in request.validated['requests']:
        subrequest = build_request(request, subrequest_spec)
        try:
            subresponse = request.invoke_subrequest(subrequest)
        except httpexceptions.HTTPException as e:
            subresponse = e
        except Exception as e:
            logger.exception(e)
            subresponse = HTTPInternalServerError()

        subresponse = build_response(subresponse, subrequest)
        responses.append(subresponse)

    return {
        'responses': responses
    }


def build_request(original, dict_obj):
    method = dict_obj.get('method') or 'GET'
    path = dict_obj['path']
    headers = dict(original.headers)
    headers.update(**dict_obj.get('headers') or {})

    payload = dict_obj.get('body') or None
    request = Request.blank(path=path,
                            headers=headers,
                            POST=payload,
                            method=method)
    return request


def build_response(response, request):
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
            pass

    dict_obj['body'] = body
    return dict_obj
