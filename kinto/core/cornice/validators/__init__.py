# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

from webob.multidict import MultiDict

from kinto.core.cornice.validators._colander import body_validator as colander_body_validator
from kinto.core.cornice.validators._colander import headers_validator as colander_headers_validator
from kinto.core.cornice.validators._colander import path_validator as colander_path_validator
from kinto.core.cornice.validators._colander import (
    querystring_validator as colander_querystring_validator,
)
from kinto.core.cornice.validators._colander import validator as colander_validator
from kinto.core.cornice.validators._marshmallow import body_validator as marshmallow_body_validator
from kinto.core.cornice.validators._marshmallow import (
    headers_validator as marshmallow_headers_validator,
)
from kinto.core.cornice.validators._marshmallow import path_validator as marshmallow_path_validator
from kinto.core.cornice.validators._marshmallow import (
    querystring_validator as marshmallow_querystring_validator,
)
from kinto.core.cornice.validators._marshmallow import validator as marshmallow_validator


__all__ = [
    "colander_validator",
    "colander_body_validator",
    "colander_headers_validator",
    "colander_path_validator",
    "colander_querystring_validator",
    "marshmallow_validator",
    "marshmallow_body_validator",
    "marshmallow_headers_validator",
    "marshmallow_path_validator",
    "marshmallow_querystring_validator",
    "extract_cstruct",
    "DEFAULT_VALIDATORS",
    "DEFAULT_FILTERS",
]


DEFAULT_VALIDATORS = []
DEFAULT_FILTERS = []


def extract_cstruct(request):
    """
    Extract attributes from the specified `request` such as body, url, path,
    method, querystring, headers, cookies, and returns them in a single dict
    object.

    :param request: Current request
    :type request: :class:`~pyramid:pyramid.request.Request`

    :returns: A mapping containing most request attributes.
    :rtype: dict
    """
    is_json = re.match("^application/(.*?)json$", str(request.content_type))

    if request.content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
        body = request.POST.mixed()
    elif request.content_type and not is_json:
        body = request.body
    else:
        if request.body:
            try:
                body = request.json_body
            except ValueError as e:
                request.errors.add("body", "", "Invalid JSON: %s" % e)
                return {}
            else:
                if not hasattr(body, "items") and not isinstance(body, list):
                    request.errors.add("body", "", "Should be a JSON object or an array")
                    return {}
        else:
            body = {}

    cstruct = {
        "method": request.method,
        "url": request.url,
        "path": request.matchdict,
        "body": body,
    }

    for sub, attr in (("querystring", "GET"), ("header", "headers"), ("cookies", "cookies")):
        data = getattr(request, attr)
        if isinstance(data, MultiDict):
            data = data.mixed()
        else:
            data = dict(data)
        cstruct[sub] = data

    return cstruct
