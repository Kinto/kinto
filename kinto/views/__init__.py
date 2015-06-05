import random
import string

from cliquet.storage import generators


class NameGenerator(generators.Generator):
    def __call__(self):
        alphabet = string.lowercase + '-'
        letters = [random.choice(alphabet) for x in range(8)]
        return ''.join(letters)
