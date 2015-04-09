import six
from uuid import uuid4


class Generator(object):
    """Generate records ids.

    Used by storage backend during record creation.
    """
    def __init__(self, config=None):
        self.config = config

    def __call__(self):
        """
        :returns: A record id, most likely unique.
        :rtype: str
        """
        raise NotImplementedError


class UUID4(Generator):
    def __call__(self):
        return six.text_type(uuid4())
