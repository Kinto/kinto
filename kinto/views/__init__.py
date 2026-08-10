import random
import string

from pyramid.httpexceptions import HTTPNotFound

from kinto.core.errors import ERRORS, http_error
from kinto.core.storage import exceptions, generators


class NameGenerator(generators.Generator):
    def __call__(self):
        alpha_num = string.ascii_letters + string.digits
        alphabet = alpha_num + "-_"
        letters = [random.SystemRandom().choice(alpha_num)]
        letters += [random.SystemRandom().choice(alphabet) for x in range(7)]

        return "".join(letters)


class RelaxedUUID(generators.UUID4):
    """A generator that generates UUIDs but accepts any string."""

    regexp = generators.Generator.regexp


def raise_404_if_invalid_id(request, resource_name, object_id):
    """Raise 404 if the specified object id does not comply with the id format
    of this kind of object, because such an object cannot exist anyway.

    :raises: :exc:`~pyramid:pyramid.httpexceptions.HTTPNotFound`
    """
    id_generators = request.registry.id_generators
    id_generator = id_generators.get(resource_name, id_generators[""])
    if not id_generator.match(object_id):
        details = {"id": object_id, "resource_name": resource_name}
        raise http_error(HTTPNotFound(), errno=ERRORS.MISSING_RESOURCE, details=details)


def object_exists_or_404(request, resource_name, object_id, parent_id=""):
    raise_404_if_invalid_id(request, resource_name, object_id)
    storage = request.registry.storage
    try:
        return storage.get(resource_name=resource_name, parent_id=parent_id, object_id=object_id)
    except exceptions.ObjectNotFoundError:
        # XXX: We gave up putting details about parent id here (See #53).
        details = {"id": object_id, "resource_name": resource_name}
        response = http_error(HTTPNotFound(), errno=ERRORS.MISSING_RESOURCE, details=details)
        raise response
