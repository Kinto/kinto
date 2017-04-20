from zope.interface import implementer

from pyramid.interfaces import ITweens

from pyramid.compat import (
    string_types,
    is_nonstr_iter,
    )

from pyramid.exceptions import ConfigurationError

from pyramid.tweens import (
    excview_tween_factory,
    MAIN,
    INGRESS,
    EXCVIEW,
    )

from pyramid.config.util import (
    action_method,
    is_string_or_iterable,
    TopologicalSorter,
    )

class TweensConfiguratorMixin(object):
    def add_tween(self, tween_factory, under=None, over=None):
        """
        .. versionadded:: 1.2

        Add a 'tween factory'.  A :term:`tween` (a contraction of 'between')
        is a bit of code that sits between the Pyramid router's main request
        handling function and the upstream WSGI component that uses
        :app:`Pyramid` as its 'app'.  Tweens are a feature that may be used
        by Pyramid framework extensions, to provide, for example,
        Pyramid-specific view timing support, bookkeeping code that examines
        exceptions before they are returned to the upstream WSGI application,
        or a variety of other features.  Tweens behave a bit like
        :term:`WSGI` 'middleware' but they have the benefit of running in a
        context in which they have access to the Pyramid :term:`application
        registry` as well as the Pyramid rendering machinery.

        .. note:: You can view the tween ordering configured into a given
                  Pyramid application by using the ``ptweens``
                  command.  See :ref:`displaying_tweens`.

        The ``tween_factory`` argument must be a :term:`dotted Python name`
        to a global object representing the tween factory.

        The ``under`` and ``over`` arguments allow the caller of
        ``add_tween`` to provide a hint about where in the tween chain this
        tween factory should be placed when an implicit tween chain is used.
        These hints are only used when an explicit tween chain is not used
        (when the ``pyramid.tweens`` configuration value is not set).
        Allowable values for ``under`` or ``over`` (or both) are:

        - ``None`` (the default).

        - A :term:`dotted Python name` to a tween factory: a string
          representing the dotted name of a tween factory added in a call to
          ``add_tween`` in the same configuration session.

        - One of the constants :attr:`pyramid.tweens.MAIN`,
          :attr:`pyramid.tweens.INGRESS`, or :attr:`pyramid.tweens.EXCVIEW`.

        - An iterable of any combination of the above. This allows the user
          to specify fallbacks if the desired tween is not included, as well
          as compatibility with multiple other tweens.
        
        ``under`` means 'closer to the main Pyramid application than',
        ``over`` means 'closer to the request ingress than'.

        For example, calling ``add_tween('myapp.tfactory',
        over=pyramid.tweens.MAIN)`` will attempt to place the tween factory
        represented by the dotted name ``myapp.tfactory`` directly 'above'
        (in ``ptweens`` order) the main Pyramid request handler.
        Likewise, calling ``add_tween('myapp.tfactory',
        over=pyramid.tweens.MAIN, under='mypkg.someothertween')`` will
        attempt to place this tween factory 'above' the main handler but
        'below' (a fictional) 'mypkg.someothertween' tween factory.

        If all options for ``under`` (or ``over``) cannot be found in the
        current configuration, it is an error. If some options are specified
        purely for compatibilty with other tweens, just add a fallback of
        MAIN or INGRESS. For example, ``under=('mypkg.someothertween',
        'mypkg.someothertween2', INGRESS)``.  This constraint will require
        the tween to be located under both the 'mypkg.someothertween' tween,
        the 'mypkg.someothertween2' tween, and INGRESS. If any of these is
        not in the current configuration, this constraint will only organize
        itself based on the tweens that are present.

        Specifying neither ``over`` nor ``under`` is equivalent to specifying
        ``under=INGRESS``.

        Implicit tween ordering is obviously only best-effort.  Pyramid will
        attempt to present an implicit order of tweens as best it can, but
        the only surefire way to get any particular ordering is to use an
        explicit tween order.  A user may always override the implicit tween
        ordering by using an explicit ``pyramid.tweens`` configuration value
        setting.

        ``under``, and ``over`` arguments are ignored when an explicit tween
        chain is specified using the ``pyramid.tweens`` configuration value.

        For more information, see :ref:`registering_tweens`.

        """
        return self._add_tween(tween_factory, under=under, over=over,
                               explicit=False)

    @action_method
    def _add_tween(self, tween_factory, under=None, over=None, explicit=False):

        if not isinstance(tween_factory, string_types):
            raise ConfigurationError(
                'The "tween_factory" argument to add_tween must be a '
                'dotted name to a globally importable object, not %r' %
                tween_factory)

        name = tween_factory

        if name in (MAIN, INGRESS):
            raise ConfigurationError('%s is a reserved tween name' % name)

        tween_factory = self.maybe_dotted(tween_factory)

        for t, p in [('over', over), ('under', under)]:
            if p is not None:
                if not is_string_or_iterable(p):
                    raise ConfigurationError(
                        '"%s" must be a string or iterable, not %s' % (t, p))

        if over is INGRESS or is_nonstr_iter(over) and INGRESS in over:
            raise ConfigurationError('%s cannot be over INGRESS' % name)

        if under is MAIN or is_nonstr_iter(under) and MAIN in under:
            raise ConfigurationError('%s cannot be under MAIN' % name)

        registry = self.registry
        introspectables = []

        tweens = registry.queryUtility(ITweens)
        if tweens is None:
            tweens = Tweens()
            registry.registerUtility(tweens, ITweens)
            ex_intr = self.introspectable('tweens',
                                          ('tween', EXCVIEW, False),
                                          EXCVIEW,
                                          'implicit tween')
            ex_intr['name'] = EXCVIEW
            ex_intr['factory'] = excview_tween_factory
            ex_intr['type'] = 'implicit'
            ex_intr['under'] = None
            ex_intr['over'] = MAIN
            introspectables.append(ex_intr)
            tweens.add_implicit(EXCVIEW, excview_tween_factory, over=MAIN)

        def register():
            if explicit:
                tweens.add_explicit(name, tween_factory)
            else:
                tweens.add_implicit(name, tween_factory, under=under, over=over)

        discriminator = ('tween', name, explicit)
        tween_type = explicit and 'explicit' or 'implicit'

        intr = self.introspectable('tweens',
                                   discriminator,
                                   name,
                                   '%s tween' % tween_type)
        intr['name'] = name
        intr['factory'] = tween_factory
        intr['type'] = tween_type
        intr['under'] = under
        intr['over'] = over
        introspectables.append(intr)
        self.action(discriminator, register, introspectables=introspectables)

@implementer(ITweens)
class Tweens(object):
    def __init__(self):
        self.sorter = TopologicalSorter(
            default_before=None,
            default_after=INGRESS,
            first=INGRESS,
            last=MAIN)
        self.explicit = []

    def add_explicit(self, name, factory):
        self.explicit.append((name, factory))

    def add_implicit(self, name, factory, under=None, over=None):
        self.sorter.add(name, factory, after=under, before=over)

    def implicit(self):
        return self.sorter.sorted()

    def __call__(self, handler, registry):
        if self.explicit:
            use = self.explicit
        else:
            use = self.implicit()
        for name, factory in use[::-1]:
            handler = factory(handler, registry)
        return handler
