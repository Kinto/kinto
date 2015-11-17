import os
import sys

from pyramid.interfaces import (
    ILocaleNegotiator,
    ITranslationDirectories,
    )

from pyramid.exceptions import ConfigurationError
from pyramid.path import package_path
from pyramid.util import action_method

class I18NConfiguratorMixin(object):
    @action_method
    def set_locale_negotiator(self, negotiator):
        """
        Set the :term:`locale negotiator` for this application.  The
        :term:`locale negotiator` is a callable which accepts a
        :term:`request` object and which returns a :term:`locale
        name`.  The ``negotiator`` argument should be the locale
        negotiator implementation or a :term:`dotted Python name`
        which refers to such an implementation.

        Later calls to this method override earlier calls; there can
        be only one locale negotiator active at a time within an
        application.  See :ref:`activating_translation` for more
        information.

        .. note::

           Using the ``locale_negotiator`` argument to the
           :class:`pyramid.config.Configurator` constructor can be used to
           achieve the same purpose.
        """
        def register():
            self._set_locale_negotiator(negotiator)
        intr = self.introspectable('locale negotiator', None,
                                   self.object_description(negotiator),
                                   'locale negotiator')
        intr['negotiator'] = negotiator
        self.action(ILocaleNegotiator, register, introspectables=(intr,))

    def _set_locale_negotiator(self, negotiator):
        locale_negotiator = self.maybe_dotted(negotiator)
        self.registry.registerUtility(locale_negotiator, ILocaleNegotiator)

    @action_method
    def add_translation_dirs(self, *specs):
        """ Add one or more :term:`translation directory` paths to the
        current configuration state.  The ``specs`` argument is a
        sequence that may contain absolute directory paths
        (e.g. ``/usr/share/locale``) or :term:`asset specification`
        names naming a directory path (e.g. ``some.package:locale``)
        or a combination of the two.

        Example:

        .. code-block:: python

           config.add_translation_dirs('/usr/share/locale',
                                       'some.package:locale')

        Later calls to ``add_translation_dir`` insert directories into the
        beginning of the list of translation directories created by earlier
        calls.  This means that the same translation found in a directory
        added later in the configuration process will be found before one
        added earlier in the configuration process.  However, if multiple
        specs are provided in a single call to ``add_translation_dirs``, the
        directories will be inserted into the beginning of the directory list
        in the order they're provided in the ``*specs`` list argument (items
        earlier in the list trump ones later in the list).
        """
        directories = []
        introspectables = []

        for spec in specs[::-1]: # reversed
            package_name, filename = self._split_spec(spec)
            if package_name is None: # absolute filename
                directory = filename
            else:
                __import__(package_name)
                package = sys.modules[package_name]
                directory = os.path.join(package_path(package), filename)

            if not os.path.isdir(os.path.realpath(directory)):
                raise ConfigurationError('"%s" is not a directory' %
                                         directory)
            intr = self.introspectable('translation directories', directory,
                                       spec, 'translation directory')
            intr['directory'] = directory
            intr['spec'] = spec
            introspectables.append(intr)
            directories.append(directory)

        def register():
            for directory in directories:

                tdirs = self.registry.queryUtility(ITranslationDirectories)
                if tdirs is None:
                    tdirs = []
                    self.registry.registerUtility(tdirs,
                                                  ITranslationDirectories)

                tdirs.insert(0, directory)

        self.action(None, register, introspectables=introspectables)

