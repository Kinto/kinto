import colander

from kinto.core import resource
from kinto.core.utils import instance_uri
from kinto.core.storage import Filter
from kinto.core.resource.viewset import ViewSet


class HistorySchema(resource.ResourceSchema):
    user_id = colander.SchemaNode(colander.String())
    uri = colander.SchemaNode(colander.String())
    action = colander.SchemaNode(colander.String())
    date = colander.SchemaNode(colander.String())
    resource_name = colander.SchemaNode(colander.String())
    bucket_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    collection_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    group_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    record_id = colander.SchemaNode(colander.String(), missing=colander.drop)
    target = colander.SchemaNode(colander.Mapping())

    class Options:
        preserve_unknown = False


# Add custom OpenAPI tags/operation ids
plural_get_arguments = getattr(ViewSet, "plural_get_arguments", {})
plural_delete_arguments = getattr(ViewSet, "plural_delete_arguments", {})

get_history_arguments = {
    "tags": ["History"],
    "operation_id": "get_history",
    **plural_get_arguments,
}
delete_history_arguments = {
    "tags": ["History"],
    "operation_id": "delete_history",
    **plural_delete_arguments,
}


@resource.register(
    name="history",
    plural_path="/buckets/{{bucket_id}}/history",
    object_path=None,
    plural_methods=("GET", "DELETE"),
    default_arguments={"tags": ["History"], **ViewSet.default_arguments},
    plural_get_arguments=get_history_arguments,
    plural_delete_arguments=delete_history_arguments,
)
class History(resource.Resource):

    schema = HistorySchema

    def get_parent_id(self, request):
        self.bucket_id = request.matchdict["bucket_id"]
        return instance_uri(request, "bucket", id=self.bucket_id)

    def _extract_filters(self):
        filters = super()._extract_filters()
        filters_str_id = []
        for filt in filters:
            if filt.field in ("record_id", "collection_id", "bucket_id"):
                if isinstance(filt.value, int):
                    filt = Filter(filt.field, str(filt.value), filt.operator)
            filters_str_id.append(filt)

        return filters_str_id
