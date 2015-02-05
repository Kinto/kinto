import colander
from cornice import Service


batch = Service(name="batch", path='/batch',
                description="Batch operations")


class BatchRequestSchema(colander.MappingSchema):
    pass


class BatchPayloadSchema(colander.MappingSchema):
    requests = colander.SchemaNode(colander.Sequence(),
                                   BatchRequestSchema())


@batch.post(permission='readonly', schema=BatchPayloadSchema)
def post_batch(request):
    responses = []

    return {
        'responses': responses
    }
