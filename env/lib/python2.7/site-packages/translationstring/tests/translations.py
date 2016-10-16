import gettext
from translationstring.compat import PY3

class Translations(gettext.GNUTranslations, object):
    """An extended translation catalog class."""

    DEFAULT_DOMAIN = 'messages'

    def __init__(self, fileobj=None, domain=DEFAULT_DOMAIN):
        """Initialize the translations catalog.

        :param fileobj: the file-like object the translation should be read
                        from
        """
        gettext.GNUTranslations.__init__(self, fp=fileobj)
        self.files = filter(None, [getattr(fileobj, 'name', None)])
        self.domain = domain
        self._domains = {}
        if fileobj is not None:
            fileobj.close()

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
            locales = [str(locale) for locale in locales]
        filename = gettext.find(domain, dirname, locales)
        fp = open(filename, 'rb')
        return cls(fileobj=fp, domain=domain)
    load = classmethod(load)
    
    def dugettext(self, domain, message):
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        if PY3: # pragma: no cover
            return self._domains.get(domain, self).gettext(message)
        else: # pragma: no cover
            return self._domains.get(domain, self).ugettext(message)
    
    def dungettext(self, domain, singular, plural, num):
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        if PY3: # pragma: no cover
            return self._domains.get(domain, self).ngettext(
                singular, plural, num)
        else: # pragma: no cover
            return self._domains.get(domain, self).ungettext(
                singular, plural, num)
        
    # Most of the downwards code, until it get's included in stdlib, from:
    #    http://bugs.python.org/file10036/gettext-pgettext.patch
    #    
    # The encoding of a msgctxt and a msgid in a .mo file is
    # msgctxt + "\x04" + msgid (gettext version >= 0.15)
    CONTEXT_ENCODING = '%s\x04%s'
