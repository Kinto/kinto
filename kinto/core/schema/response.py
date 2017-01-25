import colander

from kinto.core.schema import (ErrorSchema, ResourceSchema,
                               HeaderQuotedInteger, TimeStamp)


class RecordSchema(colander.MappingSchema):
    data = ResourceSchema(missing=colander.drop)


class CollectionSchema(colander.MappingSchema):
    data = colander.SequenceSchema(ResourceSchema(missing=colander.drop))


class ResponseHeaderSchema(colander.MappingSchema):
    etag = HeaderQuotedInteger(name='Etag')
    last_modified = colander.SchemaNode(colander.String(), name='Last-Modified')


class ErrorResponseSchema(colander.MappingSchema):
    body = ErrorSchema()


class NotModifiedResponseSchema(colander.MappingSchema):
    header = ResponseHeaderSchema()


class RecordResponseSchema(colander.MappingSchema):
    header = ResponseHeaderSchema()
    body = RecordSchema()


class CollectionResponseSchema(colander.MappingSchema):
    header = ResponseHeaderSchema()
    body = CollectionSchema()


class ResourceReponses(object):

    default_schemas = {
        '400': ErrorResponseSchema(
            description="The request is invalid."),
        '406': ErrorResponseSchema(
            description="The client doesn't accept supported responses Content-Type."),
        '412': ErrorResponseSchema(
            description="Record was changed or deleted since value in `If-Match` header."),
        'default': ErrorResponseSchema(
            description="Unexpected error."),

    }
    default_record_schemas = {
        '200': RecordResponseSchema(
            description="Return the target object.")
    }
    default_collection_schemas = {
        '200': CollectionResponseSchema(
            description="Return a list of matching objects.")
    }
    default_get_schemas = {
        '304': NotModifiedResponseSchema(
            description="Reponse has not changed since value in If-None-Match header")
    }
    default_post_schemas = {
        '200': RecordResponseSchema(
            description="Return an existing object."),
        '201': RecordResponseSchema(
            description="Return a created object."),
        '415': ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type.")
    }
    default_put_schemas = {
        '201': RecordResponseSchema(
            description="Return created object."),
        '415': ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type.")
    }
    default_patch_schemas = {
        '415': ErrorResponseSchema(
            description="The client request was not sent with a correct Content-Type.")
    }
    default_delete_schemas = {
    }
    record_get_schemas = {
        '404': ErrorResponseSchema(
            description="The object does not exist or was deleted."),
    }
    record_patch_schemas = {
        '404': ErrorResponseSchema(
            description="The object does not exist or was deleted."),
    }
    record_delete_schemas = {
        '404': ErrorResponseSchema(
            description="The object does not exist or was already deleted."),
    }

    @classmethod
    def update_record_schema(self, responses, schema):

        schema = schema.clone()
        schema['data']['last_modified'] = TimeStamp()

        for response in responses.values():
            body = response.get('body')

            # Update record schema
            if isinstance(body, RecordSchema):
                response['body'] = schema

            # Update collection schema
            elif isinstance(body, CollectionSchema):
                if 'permissions' in schema:
                    schema.__delitem__('permissions')
                response['body']['data'] = colander.SequenceSchema(schema['data'])

    @classmethod
    def get(self, endpoint_type, method, schema=None):

        responses = self.default_schemas.copy()
        type_responses = getattr(self, 'default_%s_schemas' % endpoint_type)
        responses.update(**type_responses)

        verb_responses = 'default_%s_schemas' % method.lower()
        method_args = getattr(self, verb_responses, {})
        responses.update(**method_args)

        method_responses = '%s_%s_schemas' % (endpoint_type, method.lower())
        endpoint_args = getattr(self, method_responses, {})
        responses.update(**endpoint_args)

        if schema:
            self.update_record_schema(responses, schema)

        return responses


class SharableResourseResponses(ResourceReponses):

    default_schemas = ResourceReponses.default_schemas.copy()
    default_schemas.update({
        '401': ErrorResponseSchema(
            description="The request is missing authentication headers."),
        '403': ErrorResponseSchema(
            description=("The user is not allowed to perform the operation, "
                         "or the resource is not accessible.")),
    })
