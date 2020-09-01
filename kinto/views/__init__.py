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


def object_exists_or_404(request, resource_name, object_id, parent_id=""):
    storage = request.registry.storage
    try:
        return storage.get(resource_name=resource_name, parent_id=parent_id, object_id=object_id)
    except exceptions.ObjectNotFoundError:
        # XXX: We gave up putting details about parent id here (See #53).
        details = {"id": object_id, "resource_name": resource_name}
        response = http_error(HTTPNotFound(), errno=ERRORS.MISSING_RESOURCE, details=details)
        raise response
