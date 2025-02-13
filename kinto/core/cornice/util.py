# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import warnings


__all__ = [
    "is_string",
    "to_list",
    "match_accept_header",
    "ContentTypePredicate",
    "current_service",
    "func_name",
]


def is_string(s):
    return isinstance(s, str)


def to_list(obj):
    """Convert an object to a list if it is not already one"""
    if not isinstance(obj, (list, tuple)):
        obj = [
            obj,
        ]
    return obj


def match_accept_header(func, context, request):
    """
    Return True if the request ``Accept`` header match
    the list returned by the callable specified in :param:func.

    Also attach the total list of possible accepted
    egress media types to the request.

    Utility function for performing content negotiation.

    :param func:
        The callable returning the list of acceptable
        internet media types for content negotiation.
        It obtains the request object as single argument.
    """
    acceptable = to_list(func(request))
    request.info["acceptable"] = acceptable
    return len(request.accept.acceptable_offers(acceptable)) > 0


def match_content_type_header(func, context, request):
    """
    Return True if the request ``Content-Type`` header match
    the list returned by the callable specified in :param:func.

    Also attach the total list of possible accepted
    ingress media types to the request.

    Utility function for performing request body
    media type checks.

    :param func:
        The callable returning the list of acceptable
        internet media types for request body
        media type checks.
        It obtains the request object as single argument.
    """
    supported_contenttypes = to_list(func(request))
    request.info["supported_contenttypes"] = supported_contenttypes
    return content_type_matches(request, supported_contenttypes)


def extract_json_data(request):
    warnings.warn("Use ``cornice.validators.extract_cstruct()`` instead", DeprecationWarning)
    from kinto.core.cornice.validators import extract_cstruct

    return extract_cstruct(request)["body"]


def extract_form_urlencoded_data(request):
    warnings.warn("Use ``cornice.validators.extract_cstruct()`` instead", DeprecationWarning)
    return request.POST


def content_type_matches(request, content_types):
    """
    Check whether ``request.content_type``
    matches given list of content types.
    """
    return request.content_type in content_types


class ContentTypePredicate(object):
    """
    Pyramid predicate for matching against ``Content-Type`` request header.
    Should live in ``pyramid.config.predicates``.

    .. seealso::
      http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hooks.html
      #view-and-route-predicates
    """

    def __init__(self, val, config):
        self.val = val

    def text(self):
        return "content_type = %s" % (self.val,)

    phash = text

    def __call__(self, context, request):
        return request.content_type == self.val


def func_name(f):
    """Return the name of a function or class method."""
    if isinstance(f, str):
        return f
    elif hasattr(f, "__qualname__"):  # pragma: no cover
        return f.__qualname__  # Python 3
    elif hasattr(f, "im_class"):  # pragma: no cover
        return "{0}.{1}".format(f.im_class.__name__, f.__name__)  # Python 2
    else:  # pragma: no cover
        return f.__name__  # Python 2


def current_service(request):
    """Return the Cornice service matching the specified request.

    :returns: the service or None if unmatched.
    :rtype: kinto.core.cornice.Service
    """
    if request.matched_route:
        services = request.registry.cornice_services
        pattern = request.matched_route.pattern
        name = request.matched_route.name
        # try pattern first, then route name else return None
        service = services.get(pattern, services.get("__cornice" + name))
        return service
