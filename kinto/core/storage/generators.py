import re
from uuid import uuid4


class Generator:
    """Base generator for objects ids.

    Id generators are used by storage backend during object creation, and at
    resource level to validate object id in requests paths.
    """

    regexp = r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
    """Default object id pattern. Can be changed to comply with custom ids."""

    def __init__(self, config=None):
        self.config = config
        self._regexp = None

        if not self.match(self()):
            error_msg = "Generated object id does comply with regexp."
            raise ValueError(error_msg)

    def match(self, object_id):
        """Validate that object ids match the generator. This is used mainly
        when an object id is picked arbitrarily (e.g with ``PUT`` requests).

        :returns: `True` if the specified object id matches expected format.
        :rtype: bool
        """
        if self._regexp is None:
            self._regexp = re.compile(self.regexp)
        return self._regexp.match(object_id)

    def __call__(self):
        """
        :returns: A object id, most likely unique.
        :rtype: str
        """
        raise NotImplementedError


class UUID4(Generator):
    """UUID4 object id generator.

    UUID block are separated with ``-``.
    (example: ``'472be9ec-26fe-461b-8282-9c4e4b207ab3'``)

    UUIDs are very safe in term of unicity. If 1 billion of UUIDs are generated
    every second for the next 100 years, the probability of creating just one
    duplicate would be about 50% (`source <http://en.wikipedia.org/wiki/\
Universally_unique_identifier#Random_UUID_probability_of_duplicates>`_).
    """

    regexp = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-" r"[0-9a-f]{4}-[0-9a-f]{12}$"
    """UUID4 accurate pattern."""

    def __call__(self):
        return str(uuid4())
