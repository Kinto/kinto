import logging

import colander
from cornice.validators import colander_validator
from pyramid import httpexceptions
from pyramid.security import NO_PERMISSION_REQUIRED

from kinto.core import errors
from kinto.core import Service
from kinto.core.errors import ErrorSchema
from kinto.core.utils import merge_dicts, build_request, build_response


subrequest_logger = logging.getLogger("subrequest.summary")

valid_http_method = colander.OneOf(('GET', 'HEAD', 'DELETE', 'TRACE',
                                    'POST', 'PUT', 'PATCH'))


def string_values(node, cstruct):
    """Validate that a ``colander.Mapping`` only has strings in its values.

    .. warning::

        Should be associated to a ``colander.Mapping`` schema node.
    """
    are_strings = [isinstance(v, str) for v in cstruct.values()]
    if not all(are_strings):
        error_msg = '{} contains non string value'.format(cstruct)
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

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='raise')


class BatchPayloadSchema(colander.MappingSchema):
    defaults = BatchRequestSchema(missing=colander.drop).clone()
    requests = colander.SchemaNode(colander.Sequence(),
                                   BatchRequestSchema())

    @staticmethod
    def schema_type():
        return colander.Mapping(unknown='raise')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On defaults, path is not mandatory.
        self.get('defaults').get('path').missing = colander.drop

    def deserialize(self, cstruct=colander.null):
        """Preprocess received data to carefully merge defaults.
        """
        if cstruct is not colander.null:
            defaults = cstruct.get('defaults')
            requests = cstruct.get('requests')
            if isinstance(defaults, dict) and isinstance(requests, list):
                for request in requests:
                    if isinstance(request, dict):
                        merge_dicts(request, defaults)
        return super().deserialize(cstruct)


class BatchRequest(colander.MappingSchema):
    body = BatchPayloadSchema()


class BatchResponseSchema(colander.MappingSchema):
    status = colander.SchemaNode(colander.Integer())
    path = colander.SchemaNode(colander.String())
    headers = colander.SchemaNode(colander.Mapping(unknown='preserve'),
                                  validator=string_values,
                                  missing=colander.drop)
    body = colander.SchemaNode(colander.Mapping(unknown='preserve'),
                               missing=colander.drop)


class BatchResponseBodySchema(colander.MappingSchema):
    responses = colander.SequenceSchema(BatchResponseSchema(missing=colander.drop))


class BatchResponse(colander.MappingSchema):
    body = BatchResponseBodySchema()


class ErrorResponseSchema(colander.MappingSchema):
    body = ErrorSchema()


batch_responses = {
    '200': BatchResponse(description='Return a list of operation responses.'),
    '400': ErrorResponseSchema(description='The request was badly formatted.'),
    'default': ErrorResponseSchema(description='an unknown error occurred.')
}

batch = Service(name="batch", path='/batch',
                description="Batch operations")


@batch.post(schema=BatchRequest,
            validators=(colander_validator,),
            permission=NO_PERMISSION_REQUIRED,
            tags=['Batch'], operation_id='batch',
            response_schemas=batch_responses)
def post_batch(request):
    requests = request.validated['body']['requests']

    request.log_context(batch_size=len(requests))

    limit = request.registry.settings['batch_max_requests']
    if limit and len(requests) > int(limit):
        error_msg = 'Number of requests is limited to {}'.format(limit)
        request.errors.add('body', 'requests', error_msg)
        return

    if any([batch.path in req['path'] for req in requests]):
        error_msg = 'Recursive call on {} endpoint is forbidden.'.format(batch.path)
        request.errors.add('body', 'requests', error_msg)
        return

    responses = []

    for subrequest_spec in requests:
        subrequest = build_request(request, subrequest_spec)

        log_context = {'path': subrequest.path,
                       'method': subrequest.method,
                       **request.log_context()}
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

        subrequest_logger.info('subrequest.summary', extra=log_context)

        dict_resp = build_response(resp, subrequest)
        responses.append(dict_resp)

    return {
        'responses': responses
    }
