from pyramid.interfaces import (
    IRendererFactory,
    PHASE1_CONFIG,
    )

from pyramid.util import action_method
from pyramid import renderers

DEFAULT_RENDERERS = (
    ('json', renderers.json_renderer_factory),
    ('string', renderers.string_renderer_factory),
    )

class RenderingConfiguratorMixin(object):
    def add_default_renderers(self):
        for name, renderer in DEFAULT_RENDERERS:
            self.add_renderer(name, renderer)
    
    @action_method
    def add_renderer(self, name, factory):
        """
        Add a :app:`Pyramid` :term:`renderer` factory to the
        current configuration state.

        The ``name`` argument is the renderer name.  Use ``None`` to
        represent the default renderer (a renderer which will be used for all
        views unless they name another renderer specifically).

        The ``factory`` argument is Python reference to an
        implementation of a :term:`renderer` factory or a
        :term:`dotted Python name` to same.
        """
        factory = self.maybe_dotted(factory)
        # if name is None or the empty string, we're trying to register
        # a default renderer, but registerUtility is too dumb to accept None
        # as a name
        if not name:
            name = ''
        def register():
            self.registry.registerUtility(factory, IRendererFactory, name=name)
        intr = self.introspectable('renderer factories',
                                   name,
                                   self.object_description(factory),
                                   'renderer factory')
        intr['factory'] = factory
        intr['name'] = name
        # we need to register renderers early (in phase 1) because they are
        # used during view configuration (which happens in phase 3)
        self.action((IRendererFactory, name), register, order=PHASE1_CONFIG,
                    introspectables=(intr,))

