# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import warnings
from cornice import Service
try:
    import venusian
    VENUSIAN = True
except ImportError:
    VENUSIAN = False


def resource(depth=2, **kw):
    """Class decorator to declare resources.

    All the methods of this class named by the name of HTTP resources
    will be used as such. You can also prefix them by "collection_" and they
    will be treated as HTTP methods for the given collection path
    (collection_path), if any.

    :param depth:
        Witch frame should be looked in default 2.

    :param kw:
        Keyword arguments configuring the resource.

    Here is an example::

        @resource(collection_path='/users', path='/users/{id}')
    """
    def wrapper(klass):
        return add_resource(klass, depth, **kw)
    return wrapper


def add_resource(klass, depth=1, **kw):
    """Function to declare resources of a Class.

    All the methods of this class named by the name of HTTP resources
    will be used as such. You can also prefix them by "collection_" and they
    will be treated as HTTP methods for the given collection path
    (collection_path), if any.

    :param klass:
        The class (resource) on witch to register the service.

    :param depth:
        Witch frame should be looked in default 2.

    :param kw:
        Keyword arguments configuring the resource.


    Here is an example::
        class User(object):
            pass

        add_resource(User, collection_path='/users', path='/users/{id}')
    """

    services = {}

    if 'collection_path' in kw:
        if kw['collection_path'] == kw['path']:
            msg = "Warning: collection_path and path are not distinct."
            warnings.warn(msg)

        prefixes = ('', 'collection_')
    else:
        prefixes = ('',)

    for prefix in prefixes:

        # get clean view arguments
        service_args = {}
        for k in list(kw):
            if k.startswith('collection_'):
                if prefix == 'collection_':
                    service_args[k[len(prefix):]] = kw[k]
            elif k not in service_args:
                service_args[k] = kw[k]

        if prefix == 'collection_' and service_args.get('collection_acl'):
            service_args['acl'] = service_args['collection_acl']

        # create service
        service_name = (service_args.pop('name', None) or
                        klass.__name__.lower())
        service_name = prefix + service_name
        service = services[service_name] = Service(name=service_name,
                                                   depth=2, **service_args)

        # initialize views
        for verb in ('get', 'post', 'put', 'delete', 'options', 'patch'):

            view_attr = prefix + verb
            meth = getattr(klass, view_attr, None)

            if meth is not None:
                # if the method has a __views__ arguments, then it had
                # been decorated by a @view decorator. get back the name of
                # the decorated method so we can register it properly
                views = getattr(meth, '__views__', [])
                if views:
                    for view_args in views:
                        service.add_view(verb, view_attr, klass=klass,
                                         **view_args)
                else:
                    service.add_view(verb, view_attr, klass=klass)

    setattr(klass, '_services', services)

    if VENUSIAN:
        def callback(context, name, ob):
            # get the callbacks registred by the inner services
            # and call them from here when the @resource classes are being
            # scanned by venusian.
            for service in services.values():
                config = context.config.with_package(info.module)
                config.add_cornice_service(service)

        info = venusian.attach(klass, callback, category='pyramid',
                               depth=depth)
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
    if hasattr(func, '__func__'):
        func = func.__func__
    # store view argument to use them later in @resource
    views = getattr(func, '__views__', None)
    if views is None:
        views = []
        setattr(func, '__views__', views)
    views.append(kw)
    return func
