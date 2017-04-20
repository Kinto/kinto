import re
from gettext import NullTranslations
from translationstring.compat import text_type
from translationstring.compat import string_types
from translationstring.compat import PY3

NAME_RE = r"[a-zA-Z][-a-zA-Z0-9_]*"

_interp_regex = re.compile(r'(?<!\$)(\$(?:(%(n)s)|{(%(n)s)}))'
    % ({'n': NAME_RE}))

CONTEXT_MASK = text_type('%s\x04%s')

class TranslationString(text_type):
    """
    The constructor for a :term:`translation string`.  A translation
    string is a Unicode-like object that has some extra metadata.

    This constructor accepts one required argument named ``msgid``.
    ``msgid`` must be the :term:`message identifier` for the
    translation string.  It must be a ``unicode`` object or a ``str``
    object encoded in the default system encoding.

    Optional keyword arguments to this object's constructor include
    ``domain``, ``default``, and ``mapping``.

    ``domain`` represents the :term:`translation domain`.  By default,
    the translation domain is ``None``, indicating that this
    translation string is associated with the default translation
    domain (usually ``messages``).

    ``default`` represents an explicit *default text* for this
    translation string.  Default text appears when the translation
    string cannot be translated.  Usually, the ``msgid`` of a
    translation string serves double duty as its default text.
    However, using this option you can provide a different default
    text for this translation string.  This feature is useful when the
    default of a translation string is too complicated or too long to
    be used as a message identifier. If ``default`` is provided, it
    must be a ``unicode`` object or a ``str`` object encoded in the
    default system encoding (usually means ASCII).  If ``default`` is
    ``None`` (its default value), the ``msgid`` value used by this
    translation string will be assumed to be the value of ``default``.

    ``mapping``, if supplied, must be a dictionary-like object which
    represents the replacement values for any :term:`translation
    string` *replacement marker* instances found within the ``msgid``
    (or ``default``) value of this translation string.

    ``context`` represents the :term:`translation context`.  By default,
    the translation context is ``None``.

    After a translation string is constructed, it behaves like most
    other ``unicode`` objects; its ``msgid`` value will be displayed
    when it is treated like a ``unicode`` object.  Only when its
    ``ugettext`` method is called will it be translated.

    Its default value is available as the ``default`` attribute of the
    object, its :term:`translation domain` is available as the
    ``domain`` attribute, and the ``mapping`` is available as the
    ``mapping`` attribute.  The object otherwise behaves much like a
    Unicode string.
    """
    __slots__ = ('domain', 'context', 'default', 'mapping')

    def __new__(self, msgid, domain=None, default=None, mapping=None, context=None):

        # NB: this function should never never lose the *original
        # identity* of a non-``None`` but empty ``default`` value
        # provided to it.  See the comment in ChameleonTranslate.

        self = text_type.__new__(self, msgid)
        if isinstance(msgid, self.__class__):
            domain = domain or msgid.domain and msgid.domain[:]
            context = context or msgid.context and msgid.context[:]
            default = default or msgid.default and msgid.default[:]
            mapping = mapping or msgid.mapping and msgid.mapping.copy()
            msgid = text_type(msgid)
        self.domain = domain
        self.context = context
        if default is None:
            default = text_type(msgid)
        self.default = default
        self.mapping = mapping
        return self

    def __mod__(self, options):
        """Create a new TranslationString instance with an updated mapping.
        This makes it possible to use the standard python %-style string
        formatting with translatable strings. Only dictionary
        arguments are supported.
        """
        if not isinstance(options, dict):
            raise ValueError(
                    'Can only interpolate translationstring '
                    'with dictionaries.')
        if self.mapping:
            mapping = self.mapping.copy()
            mapping.update(options)
        else:
            mapping = options.copy()
        return TranslationString(self, mapping=mapping)

    def interpolate(self, translated=None):
        """ Interpolate the value ``translated`` which is assumed to
        be a Unicode object containing zero or more *replacement
        markers* (``$foo`` or ``${bar}``) using the ``mapping``
        dictionary attached to this instance.  If the ``mapping``
        dictionary is empty or ``None``, no interpolation is
        performed.

        If ``translated`` is ``None``, interpolation will be performed
        against the ``default`` value.
        """
        if translated is None:
            translated = self.default

        # NB: this function should never never lose the *original
        # identity* of a non-``None`` but empty ``default`` value it
        # is provided.  If (translated == default) , it should return the
        # *original* default, not a derivation.  See the comment below in
        # ChameleonTranslate.

        if self.mapping and translated:
            def replace(match):
                whole, param1, param2 = match.groups()
                return text_type(self.mapping.get(param1 or param2, whole))
            translated = _interp_regex.sub(replace, translated)

        return translated

    def __reduce__(self):
        return self.__class__, self.__getstate__()

    def __getstate__(self):
        return text_type(self), self.domain, self.default, self.mapping, self.context

def TranslationStringFactory(factory_domain):
    """ Create a factory which will generate translation strings
    without requiring that each call to the factory be passed a
    ``domain`` value.  A single argument is passed to this class'
    constructor: ``domain``.  This value will be used as the
    ``domain`` values of :class:`translationstring.TranslationString`
    objects generated by the ``__call__`` of this class.  The
    ``msgid``, ``mapping``, and ``default`` values provided to the
    ``__call__`` method of an instance of this class have the meaning
    as described by the constructor of the
    :class:`translationstring.TranslationString`"""
    def create(msgid, mapping=None, default=None, context=None):
        """ Provided a msgid (Unicode object or :term:`translation
        string`) and optionally a mapping object, and a *default
        value*, return a :term:`translation string` object."""

        # if we are passing in a TranslationString as the msgid, then
        # use its domain
        if isinstance(msgid, TranslationString):
            domain = msgid.domain or factory_domain
        else:
            domain = factory_domain

        return TranslationString(msgid, domain=domain, default=default,
                                 mapping=mapping, context=context)
    return create

def ChameleonTranslate(translator):
    """
    When necessary, use the result of calling this function as a
    Chameleon template 'translate' function (e.g. the ``translate``
    argument to the ``chameleon.zpt.template.PageTemplate``
    constructor) to allow our translation machinery to drive template
    translation.  A single required argument ``translator`` is
    passsed.  The ``translator`` provided should be a callable which
    accepts a single argument ``translation_string`` ( a
    :class:`translationstring.TranslationString` instance) which
    returns a ``unicode`` object as a translation.  ``translator`` may
    also optionally be ``None``, in which case no translation is
    performed (the ``msgid`` or ``default`` value is returned
    untranslated).
    """
    def translate(msgid, domain=None, mapping=None, context=None,
                 target_language=None, default=None):

        # NB: note that both TranslationString._init__ and
        # TranslationString.interpolate are careful to never lose the
        # *identity* of an empty but non-``None`` ``default`` value we
        # provide to them.  For example, neither of those functions
        # are permitted to run an empty but non-``None`` ``default``
        # through ``unicode`` and throw the original default value
        # away afterwards.

        # This has a dubious cause: for Chameleon API reasons we must
        # ensure that, after translation, if ( (translated == msgid)
        # and (not default) and (default is not None) ) that we return
        # the ``default`` value provided to us *unmodified*, because
        # Chameleon uses it as a sentinel (it compares the return
        # value of this function by identity to what it passed in as
        # ``default``; this marker is a
        # chameleon.core.i18n.StringMarker instance, a subclass of str
        # that == '').  This is, of course, totally absurd, because
        # Chameleon *also* wants us to use ``default`` as the input to
        # a translation string in some cases, and maintaining the
        # identity of this object through translation operations isn't
        # a contract it spells out in its docs.

        # Chameleon's use of ``default`` to represent both a sentinel
        # and input to a translation string is a Chameleon i18n
        # extensibility design bug.  Until we overhaul its hook point
        # for translation extensibility, we need to appease it by
        # preserving ``default`` in the aforementioned case.  So we
        # spray these indignant comments all over this module. ;-)

        if not isinstance(msgid, string_types):
            if msgid is not None:
                msgid = text_type(msgid)
            return msgid

        tstring = msgid

        if not hasattr(tstring, 'interpolate'):
            tstring = TranslationString(msgid, domain, default, mapping, context)
        if translator is None:
            result = tstring.interpolate()
        else:
            result = translator(tstring)

        return result

    return translate

def ugettext_policy(translations, tstring, domain, context):
    """ A translator policy function which unconditionally uses the
    ``ugettext`` API on the translations object."""

    if PY3: # pragma: no cover
        _gettext = translations.gettext
    else: # pragma: no cover
        _gettext = translations.ugettext

    if context:
	# Workaround for http://bugs.python.org/issue2504?
        msgid = CONTEXT_MASK % (context, tstring)
    else:
        msgid = tstring

    translated = _gettext(msgid)
    return tstring if translated == msgid else translated

def dugettext_policy(translations, tstring, domain, context):
    """ A translator policy function which assumes the use of a
    :class:`babel.support.Translations` translations object, which
    supports the dugettext API; fall back to ugettext."""
    if domain is None:
        default_domain = getattr(translations, 'domain', None) or 'messages'
        domain = getattr(tstring, 'domain', None) or default_domain
    context = context or getattr(tstring, 'context', None)
    if context:
	# Workaround for http://bugs.python.org/issue2504?
        msgid = CONTEXT_MASK % (context, tstring)
    else:
        msgid = tstring

    if getattr(translations, 'dugettext', None) is not None:
        translated = translations.dugettext(domain, msgid)
    else:
        if PY3: # pragma: no cover
            _gettext = translations.gettext
        else: # pragma: no cover
            _gettext = translations.ugettext

        translated = _gettext(msgid)
    return tstring if translated == msgid else translated

def Translator(translations=None, policy=None):
    """
    Return a translator object based on the ``translations`` and
    ``policy`` provided.  ``translations`` should be an object
    supporting *at least* the Python :class:`gettext.NullTranslations`
    API but ideally the :class:`babel.support.Translations` API, which
    has support for domain lookups like dugettext.

    ``policy`` should be a callable which accepts three arguments:
    ``translations``, ``tstring`` and ``domain``.  It must perform the
    actual translation lookup.  If ``policy`` is ``None``, the
    :func:`translationstring.dugettext_policy` policy will be used.

    The callable returned accepts three arguments: ``tstring``
    (required), ``domain`` (optional) and ``mapping`` (optional).
    When called, it will translate the ``tstring`` translation string
    to a ``unicode`` object using the ``translations`` provided.  If
    ``translations`` is ``None``, the result of interpolation of the
    default value is returned.  The optional ``domain`` argument can
    be used to specify or override the domain of the ``tstring``
    (useful when ``tstring`` is a normal string rather than a
    translation string).  The optional ``mapping`` argument can
    specify or override the ``tstring`` interpolation mapping, useful
    when the ``tstring`` argument is a simple string instead of a
    translation string.
    """
    if policy is None:
        policy = dugettext_policy
    def translator(tstring, domain=None, mapping=None, context=None):
        if not hasattr(tstring, 'interpolate'):
            tstring = TranslationString(tstring, domain=domain, mapping=mapping, context=context)
        elif mapping:
            if tstring.mapping:
                new_mapping = tstring.mapping.copy()
                new_mapping.update(mapping)
            else:
                new_mapping = mapping
            tstring = TranslationString(tstring, domain=domain, mapping=new_mapping, context=context)
        translated = tstring
        domain = domain or tstring.domain
        context = context or tstring.context
        if translations is not None:
            translated = policy(translations, tstring, domain, context)
        if translated == tstring:
            translated = tstring.default
        if translated and '$' in translated and tstring.mapping:
            translated = tstring.interpolate(translated)
        return translated
    return translator

def ungettext_policy(translations, singular, plural, n, domain, context):
    """ A pluralizer policy function which unconditionally uses the
    ``ungettext`` API on the translations object."""

    if PY3: # pragma: no cover
        _gettext = translations.ngettext
    else: # pragma: no cover
        _gettext = translations.ungettext

    if context:
	# Workaround for http://bugs.python.org/issue2504?
        msgid = CONTEXT_MASK % (context, singular)
    else:
        msgid = singular

    translated = _gettext(msgid, plural, n)
    return singular if translated == msgid else translated

def dungettext_policy(translations, singular, plural, n, domain, context):
    """ A pluralizer policy function which assumes the use of the
    :class:`babel.support.Translations` class, which supports the
    dungettext API; falls back to ungettext."""

    default_domain = getattr(translations, 'domain', None) or 'messages'
    domain = domain or default_domain
    if context:
	# Workaround for http://bugs.python.org/issue2504?
        msgid = CONTEXT_MASK % (context, singular)
    else:
        msgid = singular
    if getattr(translations, 'dungettext', None) is not None:
        translated = translations.dungettext(domain, msgid, plural, n)
    else:
        if PY3: # pragma: no cover
            _gettext = translations.ngettext
        else: # pragma: no cover
            _gettext = translations.ungettext

        translated = _gettext(msgid, plural, n)
    return singular if translated == msgid else translated

def Pluralizer(translations=None, policy=None):
    """
    Return a pluralizer object based on the ``translations`` and
    ``policy`` provided.  ``translations`` should be an object
    supporting *at least* the Python :class:`gettext.NullTranslations`
    API but ideally the :class:`babel.support.Translations` API, which
    has support for domain lookups like dugettext.

    ``policy`` should be a callable which accepts five arguments:
    ``translations``, ``singular`` and ``plural``, ``n`` and
    ``domain``.  It must perform the actual pluralization lookup.  If
    ``policy`` is ``None``, the
    :func:`translationstring.dungettext_policy` policy will be used.

    The object returned will be a callable which has the following
    signature::

        def pluralizer(singular, plural, n, domain=None, mapping=None):
            ...

    The ``singular`` and ``plural`` objects passed may be translation
    strings or unicode strings.  ``n`` represents the number of
    elements.  ``domain`` is the translation domain to use to do the
    pluralization, and ``mapping`` is the interpolation mapping that
    should be used on the result.  Note that if the objects passed are
    translation strings, their domains and mappings are ignored.  The
    domain and mapping arguments must be used instead.  If the ``domain`` is
    not supplied, a default domain is used (usually ``messages``).
    """

    if policy is None:
        policy = dungettext_policy
    if translations is None:
        translations = NullTranslations()
    def pluralizer(singular, plural, n, domain=None, mapping=None, context=None):
        """ Pluralize this object """
        translated = text_type(
            policy(translations, singular, plural, n, domain, context))
        if translated and '$' in translated and mapping:
            return TranslationString(translated, mapping=mapping).interpolate()
        return translated
    return pluralizer
