import colander
import six

from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED

from cliquet import errors
from cliquet import logger
from cliquet import Service
from cliquet.utils import merge_dicts, build_request, build_response


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
                description="Batch operations")


@batch.post(schema=BatchPayloadSchema, permission=NO_PERMISSION_REQUIRED)
def post_batch(request):
    requests = request.validated['requests']
    batch_size = len(requests)

    limit = request.registry.settings['batch_max_requests']
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
            # Invoke subrequest without individual transaction.
            resp, subrequest = request.follow_subrequest(subrequest,
                                                         use_tweens=False)
        except httpexceptions.HTTPException as e:
            if e.content_type == 'application/json':
                resp = e
            else:
                # JSONify raw Pyramid errors.
                resp = errors.http_error(e)

        sublogger.bind(code=resp.status_code)
        sublogger.info('subrequest.summary')

        dict_resp = build_response(resp, subrequest)
        responses.append(dict_resp)

    # Rebing batch request for summary
    logger.bind(path=batch.path,
                method=request.method,
                batch_size=batch_size,
                agent=request.headers.get('User-Agent'),)

    return {
        'responses': responses
    }
