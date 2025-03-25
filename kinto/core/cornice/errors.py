# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


class Errors(list):
    """Holds Request errors"""

    def __init__(self, status=400):
        self.status = status
        super().__init__()

    def add(self, location, name=None, description=None, **kw):
        """Registers a new error."""
        allowed = ("body", "querystring", "url", "header", "path", "cookies", "method")
        if location != "" and location not in allowed:
            raise ValueError("%r not in %s" % (location, allowed))
        self.append(dict(location=location, name=name, description=description, **kw))
