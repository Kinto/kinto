from pyramid.threadlocal import get_current_registry

class ZCAConfiguratorMixin(object):
    def hook_zca(self):
        """ Call :func:`zope.component.getSiteManager.sethook` with the
        argument :data:`pyramid.threadlocal.get_current_registry`, causing
        the :term:`Zope Component Architecture` 'global' APIs such as
        :func:`zope.component.getSiteManager`,
        :func:`zope.component.getAdapter` and others to use the
        :app:`Pyramid` :term:`application registry` rather than the Zope
        'global' registry."""
        from zope.component import getSiteManager
        getSiteManager.sethook(get_current_registry)

    def unhook_zca(self):
        """ Call :func:`zope.component.getSiteManager.reset` to undo the
        action of :meth:`pyramid.config.Configurator.hook_zca`."""
        from zope.component import getSiteManager
        getSiteManager.reset()

