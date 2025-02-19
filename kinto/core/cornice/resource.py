# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import functools
import warnings

import venusian

from kinto.core.cornice import Service


def resource(depth=2, **kw):
    """Class decorator to declare resources.

    All the methods of this class named by the name of HTTP resources
    will be used as such. You can also prefix them by ``"collection_"`` and
    they will be treated as HTTP methods for the given collection path
    (collection_path), if any.

    :param depth:
        Which frame should be looked in default 2.

    :param kw:
        Keyword arguments configuring the resource.

    Here is an example::

        @resource(collection_path='/users', path='/users/{id}')
    """

    def wrapper(klass):
        return add_resource(klass, depth, **kw)

    return wrapper


def add_resource(klass, depth=2, **kw):
    """Function to declare resources of a Class.

    All the methods of this class named by the name of HTTP resources
    will be used as such. You can also prefix them by ``"collection_"`` and
    they will be treated as HTTP methods for the given collection path
    (collection_path), if any.

    :param klass:
        The class (resource) on which to register the service.

    :param depth:
        Which frame should be looked in default 2.

    :param kw:
        Keyword arguments configuring the resource.


    Here is an example:

    .. code-block:: python

        class User(object):
            pass

        add_resource(User, collection_path='/users', path='/users/{id}')

    Alternatively if you want to reuse your existing pyramid routes:

    .. code-block:: python

        class User(object):
            pass

        add_resource(User, collection_pyramid_route='users',
            pyramid_route='user')

    """

    services = {}

    if ("collection_pyramid_route" in kw or "pyramid_route" in kw) and (
        "collection_path" in kw or "path" in kw
    ):
        raise ValueError("You use either paths or route names, not both")

    if "collection_path" in kw:
        if kw["collection_path"] == kw["path"]:
            msg = "Warning: collection_path and path are not distinct."
            warnings.warn(msg)

        prefixes = ("", "collection_")
    else:
        prefixes = ("",)

    if "collection_pyramid_route" in kw:
        if kw["collection_pyramid_route"] == kw["pyramid_route"]:
            msg = "Warning: collection_pyramid_route and pyramid_route are not distinct."
            warnings.warn(msg)

        prefixes = ("", "collection_")

    for prefix in prefixes:
        # get clean view arguments
        service_args = {}
        for k in list(kw):
            if k.startswith("collection_"):
                if prefix == "collection_":
                    service_args[k[len(prefix) :]] = kw[k]
            elif k not in service_args:
                service_args[k] = kw[k]

        # auto-wire klass as its own view factory, unless one
        # is explicitly declared.
        if "factory" not in kw:
            service_args["factory"] = klass

        # create service
        service_name = service_args.pop("name", None) or klass.__name__.lower()
        service_name = prefix + service_name
        service = services[service_name] = Service(name=service_name, depth=depth, **service_args)
        # ensure the service comes with the same properties as the wrapped
        # resource
        functools.update_wrapper(service, klass)

        # initialize views
        for verb in ("get", "post", "put", "delete", "options", "patch"):
            view_attr = prefix + verb
            meth = getattr(klass, view_attr, None)

            if meth is not None:
                # if the method has a __views__ arguments, then it had
                # been decorated by a @view decorator. get back the name of
                # the decorated method so we can register it properly
                views = getattr(meth, "__views__", [])
                if views:
                    for view_args in views:
                        service.add_view(verb, view_attr, klass=klass, **view_args)
                else:
                    service.add_view(verb, view_attr, klass=klass)

    setattr(klass, "_services", services)

    def callback(context, name, ob):
        # get the callbacks registered by the inner services
        # and call them from here when the @resource classes are being
        # scanned by venusian.
        for service in services.values():
            config = context.config.with_package(info.module)
            config.add_cornice_service(service)

    info = venusian.attach(klass, callback, category="pyramid", depth=depth)

    return klass


def view(**kw):
    """Method decorator to store view arguments when defining a resource with
    the @resource class decorator

    :param kw:
        Keyword arguments configuring the view.
    """

    def wrapper(func):
        return add_view(func, **kw)

    return wrapper


def add_view(func, **kw):
    """Method to store view arguments when defining a resource with
    the add_resource class method

    :param func:
        The func to hook to

    :param kw:
        Keyword arguments configuring the view.

    Example:

    .. code-block:: python

        class User(object):

            def __init__(self, request):
                self.request = request

            def collection_get(self):
                return {'users': _USERS.keys()}

            def get(self):
                return _USERS.get(int(self.request.matchdict['id']))

        add_view(User.get, renderer='json')
        add_resource(User, collection_path='/users', path='/users/{id}')
    """
    # XXX needed in py2 to set on instancemethod
    if hasattr(func, "__func__"):  # pragma: no cover
        func = func.__func__
    # store view argument to use them later in @resource
    views = getattr(func, "__views__", None)
    if views is None:
        views = []
        setattr(func, "__views__", views)
    views.append(kw)
    return func
