from cliquet import resource, schema


class RecordSchema(schema.ResourceSchema):
    class Options():
        preserve_unknown = True


@resource.crud(path="/collections/{collection_id}/records/{id}",
               collection_path="/collections/{collection_id}/records")
class Collection(resource.BaseResource):

    mapping = RecordSchema()

    @property
    def name(self):
        return self.request.matchdict['collection_id']
