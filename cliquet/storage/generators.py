import re
from uuid import uuid4

import six


class Generator(object):
    """Generate records ids.

    Used by storage backend during record creation.
    """

    regexp = r'^[a-zA-Z0-9\-]+$'
    """Default record id pattern. Can be changed to comply with custom ids."""

    def __init__(self, config=None):
        self.config = config

        error_msg = "Generated record id does comply with regexp."
        assert self.match(self()), error_msg

    def match(self, record_id):
        """Validate that record ids match the generator. This is used mainly
        when a record id is picked arbitrarily (e.g with ``PUT`` requests).

        :returns: `True` if the specified record id matches expected format.
        :rtype: bool
        """
        return self.regexp.match(record_id)

    def __call__(self):
        """
        :returns: A record id, most likely unique.
        :rtype: str
        """
        raise NotImplementedError


class UUID4(Generator):
    regexp = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-'
                        r'[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)
    """UUID4 accurate pattern."""

    def __call__(self):
        return six.text_type(uuid4())
