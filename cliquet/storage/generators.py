import six
from uuid import uuid4

from cliquet.storage import RECORD_ID_REGEXP


class Generator(object):
    """Generate records ids.

    Used by storage backend during record creation.
    """
    def __init__(self, config=None):
        self.config = config

        error_msg = "Generated record id does comply with cliquet format."
        assert RECORD_ID_REGEXP.match(self()), error_msg

    def __call__(self):
        """
        :returns: A record id, most likely unique.
        :rtype: str
        """
        raise NotImplementedError


class UUID4(Generator):
    def __call__(self):
        return six.text_type(uuid4())
