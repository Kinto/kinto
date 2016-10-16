from webob import Response as WebobResponse

from functools import update_wrapper

from zope.interface import Interface

from pyramid.interfaces import (
    IResponse,
    ITraverser,
    IResourceURL,
    )

from pyramid.config.util import (
    action_method,
    takes_one_arg,
    )


class AdaptersConfiguratorMixin(object):
    @action_method
    def add_subscriber(self, subscriber, iface=None, **predicates):
        """Add an event :term:`subscriber` for the event stream
        implied by the supplied ``iface`` interface.

        The ``subscriber`` argument represents a callable object (or a
        :term:`dotted Python name` which identifies a callable); it will be
        called with a single object ``event`` whenever :app:`Pyramid` emits
        an :term:`event` associated with the ``iface``, which may be an
        :term:`interface` or a class or a :term:`dotted Python name` to a
        global object representing an interface or a class.

        Using the default ``iface`` value, ``None`` will cause the subscriber
        to be registered for all event types. See :ref:`events_chapter` for
        more information about events and subscribers.

        Any number of predicate keyword arguments may be passed in
        ``**predicates``.  Each predicate named will narrow the set of
        circumstances in which the subscriber will be invoked.  Each named
        predicate must have been registered via
        :meth:`pyramid.config.Configurator.add_subscriber_predicate` before it
        can be used.  See :ref:`subscriber_predicates` for more information.

        .. versionadded:: 1.4
           The ``**predicates`` argument.
        """
        dotted = self.maybe_dotted
        subscriber, iface = dotted(subscriber), dotted(iface)
        if iface is None:
            iface = (Interface,)
        if not isinstance(iface, (tuple, list)):
            iface = (iface,)

        def register():
            predlist = self.get_predlist('subscriber')
            order, preds, phash = predlist.make(self, **predicates)

            derived_predicates = [ self._derive_predicate(p) for p in preds ]
            derived_subscriber = self._derive_subscriber(
                subscriber,
                derived_predicates,
                )

            intr.update(
                {'phash':phash,
                 'order':order,
                 'predicates':preds,
                 'derived_predicates':derived_predicates,
                 'derived_subscriber':derived_subscriber,
                 }
                )

            self.registry.registerHandler(derived_subscriber, iface)
            
        intr = self.introspectable(
            'subscribers',
            id(subscriber),
            self.object_description(subscriber),
            'subscriber'
            )
        
        intr['subscriber'] = subscriber
        intr['interfaces'] = iface
        
        self.action(None, register, introspectables=(intr,))
        return subscriber

    def _derive_predicate(self, predicate):
        derived_predicate = predicate

        if eventonly(predicate):
            def derived_predicate(*arg):
                return predicate(arg[0])
            # seems pointless to try to fix __doc__, __module__, etc as
            # predicate will invariably be an instance

        return derived_predicate

    def _derive_subscriber(self, subscriber, predicates):
        derived_subscriber = subscriber

        if eventonly(subscriber):
            def derived_subscriber(*arg):
                return subscriber(arg[0])
            if hasattr(subscriber, '__name__'):
                update_wrapper(derived_subscriber, subscriber)

        if not predicates:
            return derived_subscriber

        def subscriber_wrapper(*arg):
            # We need to accept *arg and pass it along because zope subscribers
            # are designed awkwardly.  Notification via
            # registry.adapter.subscribers will always call an associated
            # subscriber with all of the objects involved in the subscription
            # lookup, despite the fact that the event sender always has the
            # option to attach those objects to the event object itself, and
            # almost always does.
            #
            # The "eventonly" jazz sprinkled in this function and related
            # functions allows users to define subscribers and predicates which
            # accept only an event argument without needing to accept the rest
            # of the adaptation arguments.  Had I been smart enough early on to
            # use .subscriptions to find the subscriber functions in order to
            # call them manually with a single "event" argument instead of
            # relying on .subscribers to both find and call them implicitly
            # with all args, the eventonly hack would not have been required.
            # At this point, though, using .subscriptions and manual execution
            # is not possible without badly breaking backwards compatibility.
            if all((predicate(*arg) for predicate in predicates)):
                return derived_subscriber(*arg)

        if hasattr(subscriber, '__name__'):
            update_wrapper(subscriber_wrapper, subscriber)

        return subscriber_wrapper
        
    @action_method
    def add_subscriber_predicate(self, name, factory, weighs_more_than=None,
                                 weighs_less_than=None):
        """
        .. versionadded:: 1.4

        Adds a subscriber predicate factory.  The associated subscriber
        predicate can later be named as a keyword argument to
        :meth:`pyramid.config.Configurator.add_subscriber` in the
        ``**predicates`` anonymous keyword argument dictionary.

        ``name`` should be the name of the predicate.  It must be a valid
        Python identifier (it will be used as a ``**predicates`` keyword
        argument to :meth:`~pyramid.config.Configurator.add_subscriber`).

        ``factory`` should be a :term:`predicate factory` or :term:`dotted
        Python name` which refers to a predicate factory.

        See :ref:`subscriber_predicates` for more information.

        """
        self._add_predicate(
            'subscriber',
            name,
            factory,
            weighs_more_than=weighs_more_than,
            weighs_less_than=weighs_less_than
            )

    @action_method
    def add_response_adapter(self, adapter, type_or_iface):
        """ When an object of type (or interface) ``type_or_iface`` is
        returned from a view callable, Pyramid will use the adapter
        ``adapter`` to convert it into an object which implements the
        :class:`pyramid.interfaces.IResponse` interface.  If ``adapter`` is
        None, an object returned of type (or interface) ``type_or_iface``
        will itself be used as a response object.

        ``adapter`` and ``type_or_interface`` may be Python objects or
        strings representing dotted names to importable Python global
        objects.

        See :ref:`using_iresponse` for more information."""
        adapter = self.maybe_dotted(adapter)
        type_or_iface = self.maybe_dotted(type_or_iface)
        def register():
            reg = self.registry
            if adapter is None:
                reg.registerSelfAdapter((type_or_iface,), IResponse)
            else:
                reg.registerAdapter(adapter, (type_or_iface,), IResponse)
        discriminator = (IResponse, type_or_iface)
        intr = self.introspectable(
            'response adapters',
            discriminator,
            self.object_description(adapter),
            'response adapter')
        intr['adapter'] = adapter
        intr['type'] = type_or_iface
        self.action(discriminator, register, introspectables=(intr,))

    def add_default_response_adapters(self):
        # cope with WebOb response objects that aren't decorated with IResponse
        self.add_response_adapter(None, WebobResponse)

    @action_method
    def add_traverser(self, adapter, iface=None):
        """
        The superdefault :term:`traversal` algorithm that :app:`Pyramid` uses
        is explained in :ref:`traversal_algorithm`.  Though it is rarely
        necessary, this default algorithm can be swapped out selectively for
        a different traversal pattern via configuration.  The section
        entitled :ref:`changing_the_traverser` details how to create a
        traverser class.

        For example, to override the superdefault traverser used by Pyramid,
        you might do something like this:

        .. code-block:: python

           from myapp.traversal import MyCustomTraverser
           config.add_traverser(MyCustomTraverser)

        This would cause the Pyramid superdefault traverser to never be used;
        instead all traversal would be done using your ``MyCustomTraverser``
        class, no matter which object was returned by the :term:`root
        factory` of this application.  Note that we passed no arguments to
        the ``iface`` keyword parameter.  The default value of ``iface``,
        ``None`` represents that the registered traverser should be used when
        no other more specific traverser is available for the object returned
        by the root factory.

        However, more than one traversal algorithm can be active at the same
        time.  The traverser used can depend on the result of the :term:`root
        factory`.  For instance, if your root factory returns more than one
        type of object conditionally, you could claim that an alternate
        traverser adapter should be used against one particular class or
        interface returned by that root factory.  When the root factory
        returned an object that implemented that class or interface, a custom
        traverser would be used.  Otherwise, the default traverser would be
        used.  The ``iface`` argument represents the class of the object that
        the root factory might return or an :term:`interface` that the object
        might implement.

        To use a particular traverser only when the root factory returns a
        particular class:

        .. code-block:: python

           config.add_traverser(MyCustomTraverser, MyRootClass)

        When more than one traverser is active, the "most specific" traverser
        will be used (the one that matches the class or interface of the
        value returned by the root factory most closely).

        Note that either ``adapter`` or ``iface`` can be a :term:`dotted
        Python name` or a Python object.

        See :ref:`changing_the_traverser` for more information.
        """
        iface = self.maybe_dotted(iface)
        adapter = self.maybe_dotted(adapter)
        def register(iface=iface):
            if iface is None:
                iface = Interface
            self.registry.registerAdapter(adapter, (iface,), ITraverser)
        discriminator = ('traverser', iface)
        intr = self.introspectable(
            'traversers', 
            discriminator,
            'traverser for %r' % iface,
            'traverser',
            )
        intr['adapter'] = adapter
        intr['iface'] = iface
        self.action(discriminator, register, introspectables=(intr,))

    @action_method
    def add_resource_url_adapter(self, adapter, resource_iface=None):
        """
        .. versionadded:: 1.3

        When you add a traverser as described in
        :ref:`changing_the_traverser`, it's convenient to continue to use the
        :meth:`pyramid.request.Request.resource_url` API.  However, since the
        way traversal is done may have been modified, the URLs that
        ``resource_url`` generates by default may be incorrect when resources
        are returned by a custom traverser.

        If you've added a traverser, you can change how
        :meth:`~pyramid.request.Request.resource_url` generates a URL for a
        specific type of resource by calling this method.

        The ``adapter`` argument represents a class that implements the
        :class:`~pyramid.interfaces.IResourceURL` interface.  The class
        constructor should accept two arguments in its constructor (the
        resource and the request) and the resulting instance should provide
        the attributes detailed in that interface (``virtual_path`` and
        ``physical_path``, in particular).

        The ``resource_iface`` argument represents a class or interface that
        the resource should possess for this url adapter to be used when
        :meth:`pyramid.request.Request.resource_url` looks up a resource url
        adapter.  If ``resource_iface`` is not passed, or it is passed as
        ``None``, the url adapter will be used for every type of resource.

        See :ref:`changing_resource_url` for more information.
        """
        adapter = self.maybe_dotted(adapter)
        resource_iface = self.maybe_dotted(resource_iface)
        def register(resource_iface=resource_iface):
            if resource_iface is None:
                resource_iface = Interface
            self.registry.registerAdapter(
                adapter,
                (resource_iface, Interface),
                IResourceURL,
                )
        discriminator = ('resource url adapter', resource_iface)
        intr = self.introspectable(
            'resource url adapters', 
            discriminator,
            'resource url adapter for resource iface %r' % resource_iface,
            'resource url adapter',
            )
        intr['adapter'] = adapter
        intr['resource_iface'] = resource_iface
        self.action(discriminator, register, introspectables=(intr,))

def eventonly(callee):
    return takes_one_arg(callee, argname='event')
