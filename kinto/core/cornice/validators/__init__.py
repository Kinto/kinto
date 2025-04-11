# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

from webob.multidict import MultiDict

from kinto.core.cornice.validators._colander import validator as colander_validator


__all__ = [
    "colander_validator",
    "extract_cstruct",
    "DEFAULT_VALIDATORS",
    "DEFAULT_FILTERS",
]


DEFAULT_VALIDATORS = []


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
