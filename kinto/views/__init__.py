import random
import string

from cliquet.storage import generators, exceptions
from pyramid import httpexceptions


class NameGenerator(generators.Generator):
    def __call__(self):
        try:
            ascii_letters = string.ascii_letters
        except ImportError:
            ascii_letters = string.letters  # NOQA
        alphabet = ascii_letters + string.digits + '-'
        letters = [random.choice(alphabet) for x in range(8)]
        return ''.join(letters)


def object_exists_or_404(request, collection_id, object_id, parent_id=''):
    storage = request.registry.storage
    try:
        storage.get(collection_id=collection_id,
                    parent_id=parent_id,
                    object_id=object_id)
    except exceptions.RecordNotFoundError:
        raise httpexceptions.HTTPNotFound()
