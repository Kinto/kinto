# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import functools
import copy
import itertools

from pyramid.httpexceptions import (HTTPMethodNotAllowed, HTTPNotAcceptable,
                                    HTTPUnsupportedMediaType, HTTPException)
from pyramid.exceptions import PredicateMismatch
from pyramid.security import NO_PERMISSION_REQUIRED

from cornice.service import decorate_view
from cornice.errors import Errors
from cornice.util import (
    is_string, to_list, match_accept_header, match_content_type_header,
    content_type_matches,
)
from cornice.cors import (
    get_cors_validator,
    get_cors_preflight_view,
    apply_cors_post_request,
    CORS_PARAMETERS
)


def make_route_factory(acl_factory):
    class ACLResource(object):
        def __init__(self, request):
            self.request = request
            self.__acl__ = acl_factory(request)

    return ACLResource


def get_fallback_view(service):
    """Fallback view for a given service, called when nothing else matches.

    This method provides the view logic to be executed when the request
    does not match any explicitly-defined view.  Its main responsibility
    is to produce an accurate error response, such as HTTPMethodNotAllowed,
    HTTPNotAcceptable or HTTPUnsupportedMediaType.
    """

    def _fallback_view(request):
        # Maybe we failed to match any definitions for the request method?
        if request.method not in service.defined_methods:
            response = HTTPMethodNotAllowed()
            response.allow = service.defined_methods
            raise response
        # Maybe we failed to match an acceptable content-type?
        # First search all the definitions to find the acceptable types.
        # XXX: precalculate this like the defined_methods list?
        acceptable = []
        supported_contenttypes = []
        for method, _, args in service.definitions:
            if method != request.method:
                continue

            if 'accept' in args:
                acceptable.extend(
                    service.get_acceptable(method, filter_callables=True))
                acceptable.extend(
                    request.info.get('acceptable', []))
                acceptable = list(set(acceptable))

                # Now check if that was actually the source of the problem.
                if not request.accept.best_match(acceptable):
                    request.errors.add(
                        'header', 'Accept',
                        'Accept header should be one of {0}'.format(
                            acceptable).encode('ascii'))
                    request.errors.status = HTTPNotAcceptable.code
                    error = service.error_handler(request.errors)
                    raise error

            if 'content_type' in args:
                supported_contenttypes.extend(
                    service.get_contenttypes(method,
                                             filter_callables=True))
                supported_contenttypes.extend(
                    request.info.get('supported_contenttypes', []))
                supported_contenttypes = list(set(supported_contenttypes))

                # Now check if that was actually the source of the problem.
                if not content_type_matches(request, supported_contenttypes):
                    request.errors.add(
                        'header', 'Content-Type',
                        'Content-Type header should be one of {0}'.format(
                            supported_contenttypes).encode('ascii'))
                    request.errors.status = HTTPUnsupportedMediaType.code
                    error = service.error_handler(request.errors)
                    raise error

        # In the absence of further information about what went wrong,
        # let upstream deal with the mismatch.
        raise PredicateMismatch(service.name)
    return _fallback_view


def apply_filters(request, response):
    if request.matched_route is not None:
        # do some sanity checking on the response using filters
        services = request.registry.cornice_services
        pattern = request.matched_route.pattern
        service = services.get(pattern, None)
        if service is not None:
            kwargs, ob = getattr(request, "cornice_args", ({}, None))
            for _filter in kwargs.get('filters', []):
                if is_string(_filter) and ob is not None:
                    _filter = getattr(ob, _filter)
                try:
                    response = _filter(response, request)
                except TypeError:
                    response = _filter(response)
            if service.cors_enabled:
                apply_cors_post_request(service, request, response)

    return response


def handle_exceptions(exc, request):
    # At this stage, the checks done by the validators had been removed because
    # a new response started (the exception), so we need to do that again.
    if not isinstance(exc, HTTPException):
        raise
    request.info['cors_checked'] = False
    return apply_filters(request, exc)


def wrap_request(event):
    """Adds a "validated" dict, a custom "errors" object and an "info" dict to
    the request object if they don't already exists
    """
    request = event.request
    request.add_response_callback(apply_filters)

    if not hasattr(request, 'validated'):
        setattr(request, 'validated', {})

    if not hasattr(request, 'errors'):
        setattr(request, 'errors', Errors(request))

    if not hasattr(request, 'info'):
        setattr(request, 'info', {})


def register_service_views(config, service):
    """Register the routes of the given service into the pyramid router.

    :param config: the pyramid configuration object that will be populated.
    :param service: the service object containing the definitions
    """
    route_name = service.name
    services = config.registry.cornice_services
    prefix = config.route_prefix or ''
    services[prefix + service.path] = service

    # before doing anything else, register a view for the OPTIONS method
    # if we need to
    if service.cors_enabled and 'OPTIONS' not in service.defined_methods:
        service.add_view('options', view=get_cors_preflight_view(service),
                         permission=NO_PERMISSION_REQUIRED)

    # register the fallback view, which takes care of returning good error
    # messages to the user-agent
    cors_validator = get_cors_validator(service)

    # Cornice-specific arguments that pyramid does not know about
    cornice_parameters = ('filters', 'validators', 'schema', 'klass',
                          'error_handler', 'deserializer') + CORS_PARAMETERS

    # 1. register route

    route_args = {}

    if hasattr(service, 'acl'):
        route_args['factory'] = make_route_factory(service.acl)

    elif hasattr(service, 'factory'):
        route_args['factory'] = service.factory

    if hasattr(service, 'traverse'):
        route_args['traverse'] = service.traverse

    config.add_route(route_name, service.path, **route_args)

    # 2. register view(s)

    for method, view, args in service.definitions:

        args = copy.copy(args)  # make a copy of the dict to not modify it
        # Deepcopy only the params we're possibly passing on to pyramid
        # (Some of those in cornice_parameters, e.g. ``schema``, may contain
        # unpickleable values.)
        for item in args:
            if item not in cornice_parameters:
                args[item] = copy.deepcopy(args[item])

        args['request_method'] = method

        if service.cors_enabled:
            args['validators'].insert(0, cors_validator)

        decorated_view = decorate_view(view, dict(args), method)

        for item in cornice_parameters:
            if item in args:
                del args[item]

        # These attributes are used in routes not views
        deprecated_attrs = ['acl', 'factory', 'traverse']
        for attr in deprecated_attrs:
            if attr in args:
                args.pop(attr)

        # pop and compute predicates which get passed through to Pyramid 1:1

        predicate_definitions = _pop_complex_predicates(args)

        if predicate_definitions:
            for predicate_list in predicate_definitions:
                args = dict(args)  # make a copy of the dict to not modify it

                # prepare view args by evaluating complex predicates
                _mungle_view_args(args, predicate_list)

                # We register the same view multiple times with different
                # accept / content_type / custom_predicates arguments
                config.add_view(view=decorated_view, route_name=route_name,
                                **args)

        else:
            # it is a simple view, we don't need to loop on the definitions
            # and just add it one time.
            config.add_view(view=decorated_view, route_name=route_name,
                            **args)

        config.commit()

    if service.definitions:
        # Add the fallback view last
        config.add_view(view=get_fallback_view(service),
                        route_name=route_name,
                        permission=NO_PERMISSION_REQUIRED)
        config.commit()


def _pop_complex_predicates(args):
    """
    Compute the cartesian product of "accept" and "content_type"
    fields to establish all possible predicate combinations.

    .. seealso::

        https://github.com/mozilla-services/cornice/pull/91#discussion_r3441384
    """

    # pop and prepare individual predicate lists
    accept_list = _pop_predicate_definition(args, 'accept')
    content_type_list = _pop_predicate_definition(args, 'content_type')

    # compute cartesian product of prepared lists, additionally
    # remove empty elements of input and output lists
    product_input = filter(None, [accept_list, content_type_list])

    # In Python 3, the filter() function returns an iterator, not a list.
    # http://getpython3.com/diveintopython3/ \
    # porting-code-to-python-3-with-2to3.html#filter
    predicate_product = list(filter(None, itertools.product(*product_input)))

    return predicate_product


def _pop_predicate_definition(args, kind):
    """
    Build a dictionary enriched by "kind" of predicate definition list.
    This is required for evaluation in ``_mungle_view_args``.
    """
    values = to_list(args.pop(kind, ()))
    # In much the same way as filter(), the map() function [in Python 3] now
    # returns an iterator. (In Python 2, it returned a list.)
    # http://getpython3.com/diveintopython3/ \
    # porting-code-to-python-3-with-2to3.html#map
    values = list(map(lambda value: {'kind': kind, 'value': value}, values))
    return values


def _mungle_view_args(args, predicate_list):
    """
    Prepare view args by evaluating complex predicates
    which get passed through to Pyramid 1:1.
    Also resolve predicate definitions passed as callables.

    .. seealso::

        https://github.com/mozilla-services/cornice/pull/91#discussion_r3441384
    """

    # map kind of argument value to function for resolving callables
    callable_map = {
        'accept': match_accept_header,
        'content_type': match_content_type_header,
    }

    # iterate and resolve all predicates
    for predicate_entry in predicate_list:

        kind = predicate_entry['kind']
        value = predicate_entry['value']

        # we need to build a custom predicate if argument value is a callable
        predicates = args.get('custom_predicates', [])
        if callable(value):
            func = callable_map.get(kind)
            if func:
                predicate_checker = functools.partial(func, value)
                predicates.append(predicate_checker)
                args['custom_predicates'] = predicates
            else:
                raise ValueError(
                    'No function defined for ' +
                    'handling callables for field "{0}"'.format(kind))
        else:
            # otherwise argument value is just a scalar
            args[kind] = value


def add_deserializer(config, content_type, deserializer):
    registry = config.registry

    def callback():
        if not hasattr(registry, 'cornice_deserializers'):
            registry.cornice_deserializers = {}
        registry.cornice_deserializers[content_type] = deserializer

    config.action(content_type, callable=callback)
