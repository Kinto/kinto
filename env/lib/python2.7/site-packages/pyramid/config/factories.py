import warnings
from zope.interface import implementer

from pyramid.interfaces import (
    IDefaultRootFactory,
    IRequestFactory,
    IResponseFactory,
    IRequestExtensions,
    IRootFactory,
    ISessionFactory,
    )

from pyramid.traversal import DefaultRootFactory

from pyramid.util import (
    action_method,
    get_callable_name,
    InstancePropertyHelper,
    )


class FactoriesConfiguratorMixin(object):
    @action_method
    def set_root_factory(self, factory):
        """ Add a :term:`root factory` to the current configuration
        state.  If the ``factory`` argument is ``None`` a default root
        factory will be registered.

        .. note::

           Using the ``root_factory`` argument to the
           :class:`pyramid.config.Configurator` constructor can be used to
           achieve the same purpose.
        """
        factory = self.maybe_dotted(factory)
        if factory is None:
            factory = DefaultRootFactory

        def register():
            self.registry.registerUtility(factory, IRootFactory)
            self.registry.registerUtility(factory, IDefaultRootFactory)  # b/c

        intr = self.introspectable('root factories',
                                   None,
                                   self.object_description(factory),
                                   'root factory')
        intr['factory'] = factory
        self.action(IRootFactory, register, introspectables=(intr,))

    _set_root_factory = set_root_factory  # bw compat

    @action_method
    def set_session_factory(self, factory):
        """
        Configure the application with a :term:`session factory`.  If this
        method is called, the ``factory`` argument must be a session
        factory callable or a :term:`dotted Python name` to that factory.

        .. note::

           Using the ``session_factory`` argument to the
           :class:`pyramid.config.Configurator` constructor can be used to
           achieve the same purpose.
        """
        factory = self.maybe_dotted(factory)

        def register():
            self.registry.registerUtility(factory, ISessionFactory)
        intr = self.introspectable('session factory', None,
                                   self.object_description(factory),
                                   'session factory')
        intr['factory'] = factory
        self.action(ISessionFactory, register, introspectables=(intr,))

    @action_method
    def set_request_factory(self, factory):
        """ The object passed as ``factory`` should be an object (or a
        :term:`dotted Python name` which refers to an object) which
        will be used by the :app:`Pyramid` router to create all
        request objects.  This factory object must have the same
        methods and attributes as the
        :class:`pyramid.request.Request` class (particularly
        ``__call__``, and ``blank``).

        See :meth:`pyramid.config.Configurator.add_request_method`
        for a less intrusive way to extend the request objects with
        custom methods and properties.

        .. note::

           Using the ``request_factory`` argument to the
           :class:`pyramid.config.Configurator` constructor
           can be used to achieve the same purpose.
        """
        factory = self.maybe_dotted(factory)

        def register():
            self.registry.registerUtility(factory, IRequestFactory)
        intr = self.introspectable('request factory', None,
                                   self.object_description(factory),
                                   'request factory')
        intr['factory'] = factory
        self.action(IRequestFactory, register, introspectables=(intr,))

    @action_method
    def set_response_factory(self, factory):
        """ The object passed as ``factory`` should be an object (or a
        :term:`dotted Python name` which refers to an object) which
        will be used by the :app:`Pyramid` as the default response
        objects. The factory should conform to the
        :class:`pyramid.interfaces.IResponseFactory` interface.

        .. note::

           Using the ``response_factory`` argument to the
           :class:`pyramid.config.Configurator` constructor
           can be used to achieve the same purpose.
        """
        factory = self.maybe_dotted(factory)

        def register():
            self.registry.registerUtility(factory, IResponseFactory)

        intr = self.introspectable('response factory', None,
                                   self.object_description(factory),
                                   'response factory')
        intr['factory'] = factory
        self.action(IResponseFactory, register, introspectables=(intr,))

    @action_method
    def add_request_method(self,
                           callable=None,
                           name=None,
                           property=False,
                           reify=False):
        """ Add a property or method to the request object.

        When adding a method to the request, ``callable`` may be any
        function that receives the request object as the first
        parameter. If ``name`` is ``None`` then it will be computed
        from the name of the ``callable``.

        When adding a property to the request, ``callable`` can either
        be a callable that accepts the request as its single positional
        parameter, or it can be a property descriptor. If ``name`` is
        ``None``, the name of the property will be computed from the
        name of the ``callable``.

        If the ``callable`` is a property descriptor a ``ValueError``
        will be raised if ``name`` is ``None`` or ``reify`` is ``True``.

        See :meth:`pyramid.request.Request.set_property` for more
        details on ``property`` vs ``reify``. When ``reify`` is
        ``True``, the value of ``property`` is assumed to also be
        ``True``.

        In all cases, ``callable`` may also be a
        :term:`dotted Python name` which refers to either a callable or
        a property descriptor.

        If ``callable`` is ``None`` then the method is only used to
        assist in conflict detection between different addons requesting
        the same attribute on the request object.

        This is the recommended method for extending the request object
        and should be used in favor of providing a custom request
        factory via
        :meth:`pyramid.config.Configurator.set_request_factory`.

        .. versionadded:: 1.4
        """
        if callable is not None:
            callable = self.maybe_dotted(callable)

        property = property or reify
        if property:
            name, callable = InstancePropertyHelper.make_property(
                callable, name=name, reify=reify)
        elif name is None:
            name = callable.__name__
        else:
            name = get_callable_name(name)

        def register():
            exts = self.registry.queryUtility(IRequestExtensions)

            if exts is None:
                exts = _RequestExtensions()
                self.registry.registerUtility(exts, IRequestExtensions)

            plist = exts.descriptors if property else exts.methods
            plist[name] = callable

        if callable is None:
            self.action(('request extensions', name), None)
        elif property:
            intr = self.introspectable('request extensions', name,
                                       self.object_description(callable),
                                       'request property')
            intr['callable'] = callable
            intr['property'] = True
            intr['reify'] = reify
            self.action(('request extensions', name), register,
                        introspectables=(intr,))
        else:
            intr = self.introspectable('request extensions', name,
                                       self.object_description(callable),
                                       'request method')
            intr['callable'] = callable
            intr['property'] = False
            intr['reify'] = False
            self.action(('request extensions', name), register,
                        introspectables=(intr,))

    @action_method
    def set_request_property(self, callable, name=None, reify=False):
        """ Add a property to the request object.

        .. deprecated:: 1.5
            :meth:`pyramid.config.Configurator.add_request_method` should be
            used instead.  (This method was docs-deprecated in 1.4 and
            issues a real deprecation warning in 1.5).

        .. versionadded:: 1.3
        """
        warnings.warn(
            'set_request_propery() is deprecated as of Pyramid 1.5; use '
            'add_request_method() with the property=True argument instead',
            DeprecationWarning,
        )
        self.add_request_method(
            callable, name=name, property=not reify, reify=reify)


@implementer(IRequestExtensions)
class _RequestExtensions(object):
    def __init__(self):
        self.descriptors = {}
        self.methods = {}
