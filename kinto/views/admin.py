"""
Special views for administration.
"""

import itertools
import colander
import collections

from kinto.authorization import RouteFactory
from kinto.core import utils as core_utils, resource
from kinto.core.events import notify_resource_event, ACTIONS
from kinto.core.resource import viewset
from kinto.core.storage import Filter


def slice_into_batches(iterable, batch_size):
    # Taken from https://code.activestate.com/recipes/303279-getting-items-in-batches/
    i = iter(iterable)
    while True:
        batchiter = itertools.islice(i, batch_size)
        try:
            yield itertools.chain([next(batchiter)], batchiter)
        except StopIteration:
            return


class Deleted(resource.ResourceSchema):
    principal = colander.SchemaNode(colander.String())

    class Options:
        preserve_unknown = False


class UserDataFactory(RouteFactory):
    method_permissions = {"delete": "delete"}


class UserDataViewSet(viewset.ShareableViewSet):
    factory = UserDataFactory


def get_parent_uri(object_uri):
    """Get the parent URI for an object_uri.

    In order to be generic over any kind of resource hierarchy, we do
    this by string manipulation on the URI instead of trying to parse
    the URI, identify the parent resource, and generate a new URI.

    """
    path = object_uri.rsplit("/", 2)
    # len(path) == 1: no '/', probably a broken URL?
    # len(path) == 2: one '/', doesn't conform to our URL scheme
    if len(path) < 3:
        return ""

    return path[0]


def condense_under_parents(request, object_uris):
    """Simplify object_uris by removing "duplicates".

    Deleting a resource usually cascades to all its descendant
    resources. Use this out-of-band knowledge to remove any objects
    which will already be deleted by virtue of deleting their
    ancestors.

    """
    # Sort object_uris so we see ancestors before descendants.
    object_uris = list(object_uris)
    object_uris.sort()

    ancestor_object_uris = set()
    for object_uri in object_uris:
        include = True
        parent_uri = get_parent_uri(object_uri)
        while parent_uri:
            if parent_uri in ancestor_object_uris:
                # It's being deleted already.
                include = False
                break
            parent_uri = get_parent_uri(parent_uri)

        if include:
            ancestor_object_uris.add(object_uri)

    return list(ancestor_object_uris)


@resource.register(
    name="user-data",
    description="Delete the data owned by a user",
    plural_path="/__user_data__",
    object_path="/__user_data__/{{principal}}",
    viewset=UserDataViewSet(),
    object_methods=("DELETE",),
)
class UserData(resource.ShareableResource):

    schema = Deleted

    def delete(self):
        principal = self.request.matchdict["principal"]
        storage = self.request.registry.storage
        permission = self.request.registry.permission
        object_uris_and_permissions = permission.get_accessible_objects([principal])
        object_uris = list(object_uris_and_permissions.keys())
        write_perm_principals = permission.get_objects_permissions(object_uris, ["write"])
        to_delete = set()
        for object_uri, principals in zip(object_uris, write_perm_principals):
            principals = principals["write"]
            # "Ownership" isn't a real concept in Kinto, so instead we
            # define ownership as meaning "this user is the only one
            # who can write to this object".
            if principals == set([principal]):
                to_delete.add(object_uri)

        # Any accessible objects that won't be deleted, need to have
        # the user's permission removed.
        for object_uri, permissions in object_uris_and_permissions.items():
            if object_uri in to_delete:
                continue

            for perm in permissions:
                permission.remove_principal_from_ace(object_uri, perm, principal)

        to_delete = condense_under_parents(self.request, to_delete)

        # Group by (parent_uri, resource of child) to make fewer
        # requests to storage backend.
        # Store the parsed object IDs, since those are what we
        # actually give to the storage backend.
        object_ids_by_parent_uri = collections.defaultdict(list)
        # Store also the object URIs, which we give to the permission backend.
        objects_by_parent_uri = collections.defaultdict(list)
        # We have to get the matchdict of the child here anyhow, so
        # keep that to generate events later.
        matchdicts_by_parent_uri = {}
        for object_uri in to_delete:
            parent_uri = get_parent_uri(object_uri)
            resource_name, matchdict = core_utils.view_lookup(self.request, object_uri)
            objects_by_parent_uri[(parent_uri, resource_name)].append(object_uri)
            object_ids_by_parent_uri[(parent_uri, resource_name)].append(matchdict["id"])
            # This overwrites previous matchdicts for the parent, but
            # we'll only use the fields that are relevant to the
            # parent, which will be the same for each child.
            matchdicts_by_parent_uri[parent_uri] = matchdict

        for (parent_uri, resource_name), object_ids in object_ids_by_parent_uri.items():
            # Generate the parent matchdict from an arbitrary child's matchdict.
            matchdict = {**matchdicts_by_parent_uri[parent_uri]}
            matchdict.pop("id", None)

            # Deletes are paginated too, so take the page size from settings.
            batch_size = self.request.registry.settings["storage_max_fetch_size"]
            for batch in slice_into_batches(object_ids, batch_size):
                batch = list(batch)
                filters = [Filter("id", batch, core_utils.COMPARISON.IN)]
                timestamp = storage.resource_timestamp(resource_name, parent_uri)
                records, _ = storage.get_all(
                    resource_name=resource_name, parent_id=parent_uri, filters=filters
                )
                tombstones = storage.delete_all(
                    resource_name=resource_name, parent_id=parent_uri, filters=filters
                )
                notify_resource_event(
                    self.request,
                    parent_uri,
                    timestamp,
                    tombstones,
                    ACTIONS.DELETE,
                    old=records,
                    resource_name=resource_name,
                    resource_data=matchdict,
                )
                # FIXME: need to purge the above tombstones, but no
                # way to purge just some tombstones for just this
                # principal

                # Clear permissions from the deleted objects, for
                # example those of other users.
                permission.delete_object_permissions(
                    *objects_by_parent_uri[(parent_uri, resource_name)]
                )

        # Remove this principal from existing users.
        permission.remove_principal(principal)

        # Remove this principal from all groups that contain it.
        associated_principals = permission.get_user_principals(principal)
        for associated_principal in associated_principals:
            permission.remove_user_principal(principal, associated_principal)

        return {"data": {"principal": principal}}
