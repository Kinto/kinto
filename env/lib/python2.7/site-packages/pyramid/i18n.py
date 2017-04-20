import gettext
import os

from translationstring import (
    Translator,
    Pluralizer,
    TranslationString, # API
    TranslationStringFactory, # API
    )

from pyramid.compat import PY2
from pyramid.decorator import reify

from pyramid.interfaces import (
    ILocalizer,
    ITranslationDirectories,
    ILocaleNegotiator,
    )

from pyramid.threadlocal import get_current_registry

TranslationString = TranslationString  # PyFlakes
TranslationStringFactory = TranslationStringFactory  # PyFlakes


class Localizer(object):
    """
    An object providing translation and pluralizations related to
    the current request's locale name.  A
    :class:`pyramid.i18n.Localizer` object is created using the
    :func:`pyramid.i18n.get_localizer` function.
    """
    def __init__(self, locale_name, translations):
        self.locale_name = locale_name
        self.translations = translations
        self.pluralizer = None
        self.translator = None

    def translate(self, tstring, domain=None, mapping=None):
        """
        Translate a :term:`translation string` to the current language
        and interpolate any *replacement markers* in the result.  The
        ``translate`` method accepts three arguments: ``tstring``
        (required), ``domain`` (optional) and ``mapping`` (optional).
        When called, it will translate the ``tstring`` translation
        string to a ``unicode`` object using the current locale.  If
        the current locale could not be determined, the result of
        interpolation of the default value is returned.  The optional
        ``domain`` argument can be used to specify or override the
        domain of the ``tstring`` (useful when ``tstring`` is a normal
        string rather than a translation string).  The optional
        ``mapping`` argument can specify or override the ``tstring``
        interpolation mapping, useful when the ``tstring`` argument is
        a simple string instead of a translation string.

        Example::

           from pyramid.18n import TranslationString
           ts = TranslationString('Add ${item}', domain='mypackage',
                                  mapping={'item':'Item'})
           translated = localizer.translate(ts)

        Example::

           translated = localizer.translate('Add ${item}', domain='mypackage',
                                            mapping={'item':'Item'})

        """
        if self.translator is None:
            self.translator = Translator(self.translations)
        return self.translator(tstring, domain=domain, mapping=mapping)

    def pluralize(self, singular, plural, n, domain=None, mapping=None):
        """
        Return a Unicode string translation by using two
        :term:`message identifier` objects as a singular/plural pair
        and an ``n`` value representing the number that appears in the
        message using gettext plural forms support.  The ``singular``
        and ``plural`` objects should be unicode strings. There is no
        reason to use translation string objects as arguments as all
        metadata is ignored.
        
        ``n`` represents the number of elements. ``domain`` is the
        translation domain to use to do the pluralization, and ``mapping``
        is the interpolation mapping that should be used on the result. If
        the ``domain`` is not supplied, a default domain is used (usually
        ``messages``).
        
        Example::

           num = 1
           translated = localizer.pluralize('Add ${num} item',
                                            'Add ${num} items',
                                            num,
                                            mapping={'num':num})

        If using the gettext plural support, which is required for
        languages that have pluralisation rules other than n != 1, the
        ``singular`` argument must be the message_id defined in the
        translation file. The plural argument is not used in this case.

        Example::

           num = 1
           translated = localizer.pluralize('item_plural',
                                            '',
                                            num,
                                            mapping={'num':num})

        
        """
        if self.pluralizer is None:
            self.pluralizer = Pluralizer(self.translations)
        return self.pluralizer(singular, plural, n, domain=domain,
                               mapping=mapping)


def default_locale_negotiator(request):
    """ The default :term:`locale negotiator`.  Returns a locale name
    or ``None``.

    - First, the negotiator looks for the ``_LOCALE_`` attribute of
      the request object (possibly set by a view or a listener for an
      :term:`event`). If the attribute exists and it is not ``None``,
      its value will be used.
  
    - Then it looks for the ``request.params['_LOCALE_']`` value.

    - Then it looks for the ``request.cookies['_LOCALE_']`` value.

    - Finally, the negotiator returns ``None`` if the locale could not
      be determined via any of the previous checks (when a locale
      negotiator returns ``None``, it signifies that the
      :term:`default locale name` should be used.)
    """
    name = '_LOCALE_'
    locale_name = getattr(request, name, None)
    if locale_name is None:
        locale_name = request.params.get(name)
        if locale_name is None:
            locale_name = request.cookies.get(name)
    return locale_name

def negotiate_locale_name(request):
    """ Negotiate and return the :term:`locale name` associated with
    the current request."""
    try:
        registry = request.registry
    except AttributeError:
        registry = get_current_registry()
    negotiator = registry.queryUtility(ILocaleNegotiator,
                                       default=default_locale_negotiator)
    locale_name = negotiator(request)

    if locale_name is None:
        settings = registry.settings or {}
        locale_name = settings.get('default_locale_name', 'en')

    return locale_name

def get_locale_name(request):
    """
    .. deprecated:: 1.5
        Use :attr:`pyramid.request.Request.locale_name` directly instead.
        Return the :term:`locale name` associated with the current request.
    """
    return request.locale_name

def make_localizer(current_locale_name, translation_directories):
    """ Create a :class:`pyramid.i18n.Localizer` object
    corresponding to the provided locale name from the 
    translations found in the list of translation directories."""
    translations = Translations()
    translations._catalog = {}

    locales_to_try = []
    if '_' in current_locale_name:
        locales_to_try = [current_locale_name.split('_')[0]]
    locales_to_try.append(current_locale_name)

    # intent: order locales left to right in least specific to most specific,
    # e.g. ['de', 'de_DE'].  This services the intent of creating a
    # translations object that returns a "more specific" translation for a
    # region, but will fall back to a "less specific" translation for the
    # locale if necessary.  Ordering from least specific to most specific
    # allows us to call translations.add in the below loop to get this
    # behavior.

    for tdir in translation_directories:
        locale_dirs = []
        for lname in locales_to_try:
            ldir = os.path.realpath(os.path.join(tdir, lname))
            if os.path.isdir(ldir):
                locale_dirs.append(ldir)

        for locale_dir in locale_dirs:
            messages_dir = os.path.join(locale_dir, 'LC_MESSAGES')
            if not os.path.isdir(os.path.realpath(messages_dir)):
                continue
            for mofile in os.listdir(messages_dir):
                mopath = os.path.realpath(os.path.join(messages_dir,
                                                       mofile))
                if mofile.endswith('.mo') and os.path.isfile(mopath):
                    with open(mopath, 'rb') as mofp:
                        domain = mofile[:-3]
                        dtrans = Translations(mofp, domain)
                        translations.add(dtrans)

    return Localizer(locale_name=current_locale_name,
                          translations=translations)

def get_localizer(request):
    """
    .. deprecated:: 1.5
        Use the :attr:`pyramid.request.Request.localizer` attribute directly
        instead.  Retrieve a :class:`pyramid.i18n.Localizer` object
        corresponding to the current request's locale name.
    """
    return request.localizer

class Translations(gettext.GNUTranslations, object):
    """An extended translation catalog class (ripped off from Babel) """

    DEFAULT_DOMAIN = 'messages'

    def __init__(self, fileobj=None, domain=DEFAULT_DOMAIN):
        """Initialize the translations catalog.

        :param fileobj: the file-like object the translation should be read
                        from
        """
        # germanic plural by default; self.plural will be overwritten by
        # GNUTranslations._parse (called as a side effect if fileobj is
        # passed to GNUTranslations.__init__) with a "real" self.plural for
        # this domain; see https://github.com/Pylons/pyramid/issues/235
        self.plural = lambda n: int(n != 1) 
        gettext.GNUTranslations.__init__(self, fp=fileobj)
        self.files = list(filter(None, [getattr(fileobj, 'name', None)]))
        self.domain = domain
        self._domains = {}

    @classmethod
    def load(cls, dirname=None, locales=None, domain=DEFAULT_DOMAIN):
        """Load translations from the given directory.

        :param dirname: the directory containing the ``MO`` files
        :param locales: the list of locales in order of preference (items in
                        this list can be either `Locale` objects or locale
                        strings)
        :param domain: the message domain
        :return: the loaded catalog, or a ``NullTranslations`` instance if no
                 matching translations were found
        :rtype: `Translations`
        """
        if locales is not None:
            if not isinstance(locales, (list, tuple)):
                locales = [locales]
            locales = [str(l) for l in locales]
        if not domain:
            domain = cls.DEFAULT_DOMAIN
        filename = gettext.find(domain, dirname, locales)
        if not filename:
            return gettext.NullTranslations()
        with open(filename, 'rb') as fp:
            return cls(fileobj=fp, domain=domain)

    def __repr__(self):
        return '<%s: "%s">' % (type(self).__name__,
                               self._info.get('project-id-version'))

    def add(self, translations, merge=True):
        """Add the given translations to the catalog.

        If the domain of the translations is different than that of the
        current catalog, they are added as a catalog that is only accessible
        by the various ``d*gettext`` functions.

        :param translations: the `Translations` instance with the messages to
                             add
        :param merge: whether translations for message domains that have
                      already been added should be merged with the existing
                      translations
        :return: the `Translations` instance (``self``) so that `merge` calls
                 can be easily chained
        :rtype: `Translations`
        """
        domain = getattr(translations, 'domain', self.DEFAULT_DOMAIN)
        if merge and domain == self.domain:
            return self.merge(translations)

        existing = self._domains.get(domain)
        if merge and existing is not None:
            existing.merge(translations)
        else:
            translations.add_fallback(self)
            self._domains[domain] = translations

        return self

    def merge(self, translations):
        """Merge the given translations into the catalog.

        Message translations in the specified catalog override any messages
        with the same identifier in the existing catalog.

        :param translations: the `Translations` instance with the messages to
                             merge
        :return: the `Translations` instance (``self``) so that `merge` calls
                 can be easily chained
        :rtype: `Translations`
        """
        if isinstance(translations, gettext.GNUTranslations):
            self._catalog.update(translations._catalog)
            if isinstance(translations, Translations):
                self.files.extend(translations.files)

        return self

    def dgettext(self, domain, message):
        """Like ``gettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).gettext(message)
    
    def ldgettext(self, domain, message):
        """Like ``lgettext()``, but look the message up in the specified 
        domain.
        """ 
        return self._domains.get(domain, self).lgettext(message)
    
    def dugettext(self, domain, message):
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        if PY2:
            return self._domains.get(domain, self).ugettext(message)
        else:
            return self._domains.get(domain, self).gettext(message)
    
    def dngettext(self, domain, singular, plural, num):
        """Like ``ngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ngettext(singular, plural, num)
    
    def ldngettext(self, domain, singular, plural, num):
        """Like ``lngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).lngettext(singular, plural, num)
    
    def dungettext(self, domain, singular, plural, num):
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        if PY2:
            return self._domains.get(domain, self).ungettext(
                singular, plural, num)
        else:
            return self._domains.get(domain, self).ngettext(
                singular, plural, num)

class LocalizerRequestMixin(object):
    @reify
    def localizer(self):
        """ Convenience property to return a localizer """
        registry = self.registry

        current_locale_name = self.locale_name
        localizer = registry.queryUtility(ILocalizer, name=current_locale_name)

        if localizer is None:
            # no localizer utility registered yet
            tdirs = registry.queryUtility(ITranslationDirectories, default=[])
            localizer = make_localizer(current_locale_name, tdirs)

            registry.registerUtility(localizer, ILocalizer,
                                     name=current_locale_name)

        return localizer

    @reify
    def locale_name(self):
        locale_name = negotiate_locale_name(self)
        return locale_name
        
    
