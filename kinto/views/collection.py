from cliquet import resource, schema


class RecordSchema(schema.ResourceSchema):
    class Options():
        preserve_unknown = True


@resource.register(
    name="collection",
    record_path=("/buckets/{{bucket_id}}"
                 "/collections/{{collection_id}}/records/{{id}}"),
    collection_path=("/buckets/{{bucket_id}}"
                     "/collections/{{collection_id}}/records"))
class Collection(resource.BaseResource):

    mapping = RecordSchema()

    def __init__(self, *args, **kwargs):
        super(Collection, self).__init__(*args, **kwargs)
        self.collection.collection_id = self.request.matchdict['collection_id']
        self.collection.parent_id = self.request.matchdict['bucket_id']

    def is_known_field(self, field_name):
        """Without schema, any field is considered as known."""
        return True
