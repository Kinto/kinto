import random
import string

from cliquet.storage import generators


class NameGenerator(generators.Generator):
    def __call__(self):
        try:
            ascii_letters = string.ascii_letters
        except ImportError:
            ascii_letters = string.letters  # NOQA
        alphabet = ascii_letters + string.digits + '-'
        letters = [random.choice(alphabet) for x in range(8)]
        return ''.join(letters)
