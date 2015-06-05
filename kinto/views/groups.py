import colander

from cliquet import resource
from cliquet import schema

from kinto.views import NameGenerator, object_exists_or_404


class GroupSchema(schema.ResourceSchema):
    members = colander.SchemaNode(colander.Sequence(),
                                  colander.SchemaNode(colander.String()))


groups_options = {
    'collection_path': "/buckets/{{bucket_id}}/groups",
    'record_path': "/buckets/{{bucket_id}}/groups/{{id}}"
}


@resource.register(name="group", **groups_options)
class Group(resource.BaseResource):

    mapping = GroupSchema()

    def __init__(self, *args, **kwargs):
        super(Group, self).__init__(*args, **kwargs)

        bucket_id = self.request.matchdict['bucket_id']
        object_exists_or_404(self.request,
                             collection_id='bucket',
                             object_id=bucket_id)

        parent_id = '/buckets/%s' % bucket_id
        self.collection.parent_id = parent_id
        self.collection.id_generator = NameGenerator()
