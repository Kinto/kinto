import random
import string

from cliquet import resource
from cliquet.storage import generators


class NameGenerator(generators.Generator):
    def __call__(self):
        alphabet = string.lowercase + '-'
        letters = [random.choice(alphabet) for x in range(8)]
        return ''.join(letters)


buckets_options = {
    'collection_methods': ('GET',)
}


@resource.register(name="bucket", **buckets_options)
class Bucket(resource.BaseResource):

    def __init__(self, *args, **kwargs):
        super(Bucket, self).__init__(*args, **kwargs)
        self.collection.id_generator = NameGenerator()
