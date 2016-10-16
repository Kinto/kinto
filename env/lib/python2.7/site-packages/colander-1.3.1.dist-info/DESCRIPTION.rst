Colander
========

.. image:: https://travis-ci.org/Pylons/colander.svg?branch=master
        :target: https://travis-ci.org/Pylons/colander

.. image:: https://readthedocs.org/projects/colander/badge/?version=master
        :target: http://docs.pylonsproject.org/projects/colander/en/master/
        :alt: Documentation Status

An extensible package which can be used to:

- deserialize and validate a data structure composed of strings,
  mappings, and lists.

- serialize an arbitrary data structure to a data structure composed
  of strings, mappings, and lists.

It is tested on Python 2.7, 3.3, 3.4, and 3.5, and PyPy.

Please see http://docs.pylonsproject.org/projects/colander/en/latest/
for documentation.

See https://github.com/Pylons/colander for in-development version.


1.3.1 (2016-05-23)
==================

- 1.3 was released without updating the changelog. This release fixes that.

1.3 (2016-05-23)
================

- Drop Python 2.6 and PyPy3 from the test suite. They are no longer
  supported. See https://github.com/Pylons/colander/pull/263

- ``colander.String`` schema type now supports an optional keyword argument
  ``allow_empty`` which, when True, deserializes an empty string to an
  empty string. When False (default), an empty string deserializes to
  ``colander.null``. This allows for a node to be explicitly required, but
  allow an empty ('') value to be provided.
  https://github.com/Pylons/colander/issues/199

- Add ``separator`` parameter to ``colander.Invalid.asdict``
  (for backward compatibility, default is '; ').
  See https://github.com/Pylons/colander/pull/253

- Fixed an issue with ``SchemaNode.clone`` where it would fail when
  cloning an instance of ``colander.SequenceSchema`` due to initializing
  the schema without any children, violating some checks.
  See https://github.com/Pylons/colander/pull/212

1.2 (2016-01-18)
================

Features
--------

- Add new exception `UnsupportedFields`. Used to pass to the caller a list
  of extra fields detected in a cstruct during deserialize.
  See https://github.com/Pylons/colander/pull/241

- Add ``drop`` functionality to ``Sequence`` type.
  See https://github.com/Pylons/colander/pull/225

Bug Fixes
---------

- ``SchemaNode`` will no longer assume the first argument to the constructor
  is the schema type. This allows it to properly fallback to using the
  ``schema_type`` class attribute on subclasses even when using the
  imperative API to pass options to the constructor.

- Fix a bug in which ``MappingSchema``, ``SequenceSchema`` and
  ``TupleSchema`` would always treat the first arg as the schema type. This
  meant that it would fail if passed only nodes to the constructor despite
  the default type being implied by the name. It is now possible to do
  ``MappingSchema(child1, child2, ...)`` instead of
  ``MappingSchema(Mapping(), child1, child2)``.

Translations
------------

- Added Finnish translations: ``fi``
  See https://github.com/Pylons/colander/pull/243

1.1 (2016-01-15)
================

Platform
--------

- Add explicit support for Python 3.4, Python 3.5 and PyPy3.

Features
--------

- Add ``min_err`` and ``max_err`` arguments to ``Length``, allowing
  customization of its error messages.

- Add ``colander.Any`` validator: succeeds if at least one of its
  subvalidators succeeded.

- Allow localization of error messages returned by ``colander.Invalid.asdict``
  by adding an optional ``translate`` callable argument.

- Add a ``missing_msg`` argument to ``SchemaNode``, allowing customization
  of the error message used when the node is required and missing.

- Add `NoneOf` validator wich succeeds if the value is none of the choices.

- Add ``normalize`` option to ``Decimal``, stripping the rightmost
  trailing zeros.

Bug Fixes
---------

- Fix an issue where the ``flatten()`` method produces an invalid name
  (ex: "answer.0.") for the type ``Sequence``.  See
  https://github.com/Pylons/colander/issues/179

- Fixed issue with ``String`` not being properly encoded when non-string
  values were passed into ``serialize()``
  See `#235 <https://github.com/Pylons/colander/pull/235>`_

- ``title`` was being overwritten when made a child through defining a schema
  as a class. See https://github.com/Pylons/colander/pull/239

Translations
------------

- Added new translations: ``el``

- Updated translations: ``fr``, ``de``, ``ja``

1.0 (2014-11-26)
================

Backwards Incompatibilities
---------------------------

- ``SchemaNode.deserialize`` will now raise an
  ``UnboundDeferredError`` if the node has an unbound deferred
  validator.  Previously, deferred validators were silently ignored.
  See https://github.com/Pylons/colander/issues/47

Bug Fixes
---------

- Removed forked ``iso8601`` and change to dependency on PyPI ``iso8601``
  (due to float rounding bug on microsecond portion when parsing
  iso8601 datetime string).  Left an ``iso8601.py`` stub for backwards
  compatibility.

- Time of "00:00" no longer gives ``colander.Invalid``.

- Un-break wrapping of callable instances as ``colander.deferred``.
  See https://github.com/Pylons/colander/issues/141.

- Set the max length TLD to 22 in ``Email`` validator based on the
  current list of valid TLDs.
  See https://github.com/Pylons/colander/issues/159

- Fix an issue where ``drop`` was not recognized as a default and was
  returning the ``drop`` instance instead of omitting the value.
  https://github.com/Pylons/colander/issues/139

- Fix an issue where the ``SchemaNode.title`` was clobbered by the ``name``
  when defined as a class attribute.
  See https://github.com/Pylons/colander/pull/183 and
  https://github.com/Pylons/colander/pull/185

Translations
------------

- Updated translations: ``fr``, ``de``, ``ja``


1.0b1 (2013-09-01)
==================

Bug Fixes
---------

- In 1.0a1, there was a change merged from
  https://github.com/Pylons/colander/pull/73 which made it possible to supply
  ``None`` as the ``default`` value for a String type, and upon serialization,
  the value would be rendered as ``colander.null`` if the default were used.
  This confused people who were actually supplying the value ``None`` as a
  default when the associated appstruct had no value, so the change has been
  reverted.  When you supply ``None`` as the ``default`` argument to a String,
  the rendered serialize() value will again be ``'None'``.  Sorry.

- Normalize ``colander.Function`` argument ``message`` to be ``msg``. This now
  matches other APIs within Colander. The ``message`` argument is now
  deprecated and a warning will be emitted.
  https://github.com/Pylons/colander/issues/31
  https://github.com/Pylons/colander/issues/64

- ``iso8601.py``:  Convert ``ValueError`` (raised by ``datetime``) into
  ``ParseErrorr`` in ``parse_date``, so that the validation machinery
  upstream handles it properly.

- ``iso8601.py``:  Correctly parse datetimes with a timezone of Z even
  when the default_timezone is set. These previously had the default
  timezone.

- ``colander.String`` schema type now raises ``colander.Invalid`` when trying
  to deserialize a non-string item.
  See https://github.com/Pylons/colander/issues/100

Features
--------

- Add ``colander.List`` type, modeled on ``deform.List``:  this type
  preserves ordering, and allows duplicates.

- It is now possible to use the value ``colander.drop`` as the ``default``
  value for items that are subitems of a mapping.  If ``colander.drop`` is used
  as the ``default`` for a subnode of a mapping schema, and the mapping
  appstruct being serialized does not have a value for that schema node, the
  value will be omitted from the serialized mapping.  For instance, the
  following script, when run would not raise an assertion error::

      class What(colander.MappingSchema):
        thing = colander.SchemaNode(colander.String(), default=colander.drop)

      result = What().serialize({}) # no "thing" in mapping
      assert result == {}

- The ``typ`` of a ``SchemaNode`` can optionally be pased in as a keyword
  argument. See https://github.com/Pylons/colander/issues/90

- Allow interpolation of `missing_msg` with properties `title` and `name`

1.0a5 (2013-05-31)
==================

- Fix bug introduced by supporting spec-mandated truncations of ISO-8601
  timezones.  A TypeError would be raised instead of Invalid.  See
  https://github.com/Pylons/colander/issues/111.

1.0a4 (2013-05-21)
==================

- Loosen Email validator regex (permit apostrophes, bang, etc in localpart).

- Allow for timezone info objects to be pickled and unpickled "more correctly"
  (Use '__getinitargs__' to provide unpickling-only defaults).  See
  https://github.com/Pylons/colander/pull/108.

1.0a3 (2013-05-16)
==================

Features
--------

- Support spec-mandated truncations of ISO-8601 timezones.

- Support spec-mandated truncations of ISO-8601 datetimes.

- Allow specifying custom representations of values for boolean fields.

Bug Fixes
---------

- Ensure that ``colander.iso8601.FixedOffset`` instances can be unpickled.

- Avoid validating strings as sequences under Py3k.

- Sync documentation with 0.9.9 change to use ``insert_before`` rather than
  ``schema_order``.  See https://github.com/Pylons/colander/issues/104


1.0a2 (2013-01-30)
==================

Features
--------

- Add ``colander.ContainsOnly`` and ``colander.url`` validators.

- Add ``colander.instantiate`` to help define schemas containing
  mappings and sequences more succinctly.

1.0a1 (2013-01-10)
==================

Bug Fixes
---------

- Work around a regression in Python 3.3 for ``colander.Decimal`` when it's
  used with a ``quant`` argument but without a ``rounding`` argument.
  See https://github.com/Pylons/colander/issues/66

- Using ``SchemaNode(String, default='', ..)`` now works properly, or at least
  more intuitively.  Previously if an empty-string ``default`` was supplied,
  serialization would return a defaulted value as ``colander.null``.  See
  https://github.com/Pylons/colander/pull/73.

- Stricter checking in colander.Mapping to prevent items which are logically
  not mappings from being accepted during validation (see
  https://github.com/Pylons/colander/pull/96).

Features
--------

- Add ``colander.Set`` type, ported from ``deform.Set``

- Add Python 3.3 to tox configuration and use newer tox testing regime
  (setup.py dev).

- Add Python 3.3 Trove classifier.

- Calling ``bind`` on a schema node e.g. ``cloned_node = somenode.bind(a=1,
  b=2)`` on a schema node now results in the cloned node having a
  ``bindings`` attribute of the value ``{'a':1, 'b':2}``.

- It is no longer necessary to pass a ``typ`` argument to a SchemaNode
  constructor if the node class has a ``schema_type`` callable as a class
  attribute which, when called with no arguments, returns a schema type.
  This callable will be called to obtain the schema type if a ``typ`` is not
  supplied to the constructor.  The default ``SchemaNode`` object's
  ``schema_type`` callable raises a ``NotImplementedError`` when it is
  called.

- SchemaNode now has a ``raise_invalid`` method which accepts a message and
  raises a colander.Invalid exception using ``self`` as the node and the
  message as its message.

- It is now possible and advisable to subclass ``SchemaNode`` in order to
  create a bundle of default node behavior.  The subclass can define the
  following methods and attributes: ``preparer``, ``validator``, ``default``,
  ``missing``, ``name``, ``title``, ``description``, ``widget``, and
  ``after_bind``.

  For example, the older, more imperative style that looked like this still
  works, of course::

     from colander import SchemaNode

     ranged_int = colander.SchemaNode(
         validator=colander.Range(0, 10),
         default = 10,
         title='Ranged Int'
         )

  But you can alternately now do something like this::

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         validator = colander.Range(0, 10)
         default = 10
         title = 'Ranged Int'

     ranged_int = RangedInt()

  Values that are expected to be callables can now alternately be methods of
  the schemanode subclass instead of plain attributes::

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         def validator(self, node, cstruct):
            if not 0 < cstruct < 10:
                raise colander.Invalid(node, 'Must be between 0 and 10')

     ranged_int = RangedInt()

  Note that when implementing a method value such as ``validator`` that
  expects to receive a ``node`` argument, ``node`` must be provided in the
  call signature, even though ``node`` will almost always be the same as
  ``self``.  This is because Colander simply treats the method as another
  kind of callable, be it a method, or a function, or an instance that has a
  ``__call__`` method.  It doesn't care that it happens to be a method of
  ``self``, and it needs to support callables that are not methods, so it
  sends ``node`` in regardless.

  You can't currently use *method* definitions as ``colander.deferred``
  callables.  For example this will *not* work::

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         @colander.deferred
         def validator(self, node, kw):
            request = kw['request']
            def avalidator(node, cstruct):
                if not 0 < cstruct < 10:
                    if request.user != 'admin':
                        raise colander.Invalid(node, 'Must be between 0 and 10')
            return avalidator

     ranged_int = RangedInt()
     bound_ranged_int = ranged_int.bind(request=request)

  This will result in::

        TypeError: avalidator() takes exactly 3 arguments (2 given)

  However, if you treat the thing being decorated as a function instead of a
  method (remove the ``self`` argument from the argument list), it will
  indeed work)::

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         @colander.deferred
         def validator(node, kw):
            request = kw['request']
            def avalidator(node, cstruct):
                if not 0 < cstruct < 10:
                    if request.user != 'admin':
                        raise colander.Invalid(node, 'Must be between 0 and 10')
            return avalidator

     ranged_int = RangedInt()
     bound_ranged_int = ranged_int.bind(request=request)

  In previous releases of Colander, the only way to defer the computation of
  values was via the ``colander.deferred`` decorator.  In this release,
  however, you can instead use the ``bindings`` attribute of ``self`` to
  obtain access to the bind parameters within values that are plain old
  methods::

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'

         def validator(self, node, cstruct):
            request = self.bindings['request']
            if not 0 < cstruct < 10:
                if request.user != 'admin':
                    raise colander.Invalid(node, 'Must be between 0 and 10')

     ranged_int = RangedInt()
     bound_range_int = ranged_int.bind(request=request)

  If the things you're trying to defer aren't callables like ``validator``,
  but they're instead just plain attributes like ``missing`` or ``default``,
  instead of using a ``colander.deferred``, you can use ``after_bind`` to set
  attributes of the schemanode that rely on binding variables::

     from colander import SchemaNode

     class UserIdSchemaNode(SchemaNode):
         title = 'User Id'

         def after_bind(self, node, kw):
             self.default = kw['request'].user.id

  You can override the default values of a schemanode subclass in its
  constructor::

     from colander import SchemaNode

     class RangedIntSchemaNode(SchemaNode):
         default = 10
         title = 'Ranged Int'
         validator = colander.Range(0, 10)

     ranged_int = RangedInt(validator=colander.Range(0, 20))

  In the above example, the validation will be done on 0-20, not 0-10.

  If a schema node name conflicts with a schema value attribute name on the
  same class, you can work around it by giving the schema node a bogus name
  in the class definition but providing a correct ``name`` argument to the
  schema node constructor::

     from colander import SchemaNode, Schema

     class SomeSchema(Schema):
         title = 'Some Schema'
         thisnamewillbeignored = colander.SchemaNode(
                                             colander.String(),
                                             name='title'
                                             )

  Note that such a workaround is only required if the conflicting names are
  attached to the *exact same* class definition.  Colander scrapes off schema
  node definitions at each class' construction time, so it's not an issue for
  inherited values.  For example::

     from colander import SchemaNode, Schema

     class SomeSchema(Schema):
         title = colander.SchemaNode(colander.String())

     class AnotherSchema(SomeSchema):
         title = 'Some Schema'

     schema = AnotherSchema()

  In the above example, even though the ``title = 'Some Schema'`` appears to
  override the superclass' ``title`` SchemaNode, a ``title`` SchemaNode will
  indeed be present in the child list of the ``schema`` instance
  (``schema['title']`` will return the ``title`` SchemaNode) and the schema's
  ``title`` attribute will be ``Some Schema`` (``schema.title`` will return
  ``Some Schema``).

  Normal inheritance rules apply to class attributes and methods defined in
  a schemanode subclass.  If your schemanode subclass inherits from another
  schemanode class, your schemanode subclass' methods and class attributes
  will override the superclass' methods and class attributes.

  Ordering of child schema nodes when inheritance is used works like this:
  the "deepest" SchemaNode class in the MRO of the inheritance chain is
  consulted first for nodes, then the next deepest, then the next, and so on.
  So the deepest class' nodes come first in the relative ordering of schema
  nodes, then the next deepest, and so on.  For example::

      class One(colander.Schema):
          a = colander.SchemaNode(
              colander.String(),
              id='a1',
              )
          b = colander.SchemaNode(
              colander.String(),
              id='b1',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d1',
              )

      class Two(One):
          a = colander.SchemaNode(
              colander.String(),
              id='a2',
              )
          c = colander.SchemaNode(
              colander.String(),
              id='c2',
              )
          e = colander.SchemaNode(
              colander.String(),
              id='e2',
              )

      class Three(Two):
          b = colander.SchemaNode(
              colander.String(),
              id='b3',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d3',
              )
          f = colander.SchemaNode(
              colander.String(),
              id='f3',
              )

      three = Three()

  The ordering of child nodes computed in the schema node ``three`` will be
  ``['a2', 'b3', 'd3', 'c2', 'e2', 'f3']``.  The ordering starts ``a1``,
  ``b1``, ``d1`` because that's the ordering of nodes in ``One``, and
  ``One`` is the deepest SchemaNode in the inheritance hierarchy.  Then it
  processes the nodes attached to ``Two``, the next deepest, which causes
  ``a1`` to be replaced by ``a2``, and ``c2`` and ``e2`` to be appended to
  the node list.  Then finally it processes the nodes attached to ``Three``,
  which causes ``b1`` to be replaced by ``b3``, and ``d1`` to be replaced by
  ``d3``, then finally ``f`` is appended.

  Multiple inheritance works the same way::

      class One(colander.Schema):
          a = colander.SchemaNode(
              colander.String(),
              id='a1',
              )
          b = colander.SchemaNode(
              colander.String(),
              id='b1',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d1',
              )

      class Two(colander.Schema):
          a = colander.SchemaNode(
              colander.String(),
              id='a2',
              )
          c = colander.SchemaNode(
              colander.String(),
              id='c2',
              )
          e = colander.SchemaNode(
              colander.String(),
              id='e2',
              )

      class Three(Two, One):
          b = colander.SchemaNode(
              colander.String(),
              id='b3',
              )
          d = colander.SchemaNode(
              colander.String(),
              id='d3',
              )
          f = colander.SchemaNode(
              colander.String(),
              id='f3',
              )

      three = Three()

  The resulting node ordering of ``three`` is the same as the single
  inheritance example: ``['a2', 'b3', 'd3', 'c2', 'e2', 'f3']`` due to the
  MRO deepest-first ordering (``One``, then ``Two``, then ``Three``).

Backwards Incompatibilities
---------------------------

- Passing non-SchemaNode derivative instances as ``*children`` into a
  SchemaNode constructor is no longer supported.  Symptom: ``AttributeError:
  name`` when constructing a SchemaNode.

0.9.9 (2012-09-24)
==================

Features
--------

- Allow the use of ``missing=None`` for Number.  See
  https://github.com/Pylons/colander/pull/59 .

- Create a ``colander.Money`` type that is a Decimal type with
  two-decimal-point precision rounded-up.

- Allow ``quant`` and ``rounding`` args to ``colander.Decimal`` constructor.

- ``luhnok`` validator added (credit card luhn mod10 validator).

- Add an ``insert`` method to SchemaNode objects.

- Add an ``insert_before`` method to SchemaNode objects.

- Better class-based mapping schema inheritance model.

  * A node declared in a subclass of a mapping schema superclass now
    overrides any node with the same name inherited from any superclass.
    Previously, it just repeated and didn't override.

  * An ``insert_before`` keyword argument may be passed to a SchemaNode
    constructor.  This is a string naming a node in a superclass.  A node
    with an ``insert_before`` will be placed before the named node in a
    parent mapping schema.

- The ``preparer=`` argument to SchemaNodes may now be a sequence of
  preparers.

- Added a ``cstruct_children`` method to SchemaNode.

- A new ``cstruct_children`` API should exist on schema types.  If
  ``SchemaNode.cstruct_children`` is called on a node with a type that does
  not have a ``cstruct_children`` method, a deprecation warning is emitted
  and ``[]`` is returned (this may or may not be the correct value for your
  custom type).

Backwards Incompatibilities
---------------------------

- The inheritance changes required a minor backwards incompatibility: calling
  ``__setitem__`` on a SchemaNode will no longer raise ``KeyError`` when
  attempting to set a subnode into a node that doesn't already have an
  existing subnode by that name.  Instead, the subnode will be appended to
  the child list.

Documentation
-------------

- A "Schema Inheritance" section was added to the Basics chapter
  documentation.

0.9.8 (2012-04-27)
==================

- False evaluating values are now serialized to colander.null for
  String, Date, and Time.  This resolves the issue where a None value
  would be rendered as 'None' for String, and missing='None' was not
  possible for Date, Datetime, and Time.
  See https://github.com/Pylons/colander/pull/1 .

- Updated Brazilian Portugese translations.

- Updated Japanese translations.

- Updated Russian translations.

- Fix documentation: 0.9.3 allowed explicitly passing None to DateTime
  to have no default timezone applied.

- Add ``dev`` and ``docs`` setup.py aliases (e.g. ``python setup.py dev``).

0.9.7 (2012-03-20)
==================

- Using ``schema.flatten(...)`` against a mapping schema node without a name
  produced incorrectly dot-prefixed keys.  See
  https://github.com/Pylons/colander/issues/37

- Fix invalid.asdict for multiple error messages.  See
  https://github.com/Pylons/colander/pull/22 ,
  https://github.com/Pylons/colander/pull/27 ,
  https://github.com/Pylons/colander/pull/12 , and
  https://github.com/Pylons/colander/issues/2 .

- Invalid.messages() now returns an empty list if there are no messages.
  See https://github.com/Pylons/colander/pull/21 .

- ``name`` passed to a SchemaNode constructor was not respected in
  declaratively constructed schemas.  Now if you pass ``name`` to the
  SchemaNode constructor within the body of a schema class, it will take
  precedence over the name it's been assigned to in the schema class.
  See https://github.com/Pylons/colander/issues/39 .

- Japanese translation thanks to OCHIAI, Gouji.

- Replaced incorrect ``%{err}`` with correct ``${err}`` in String.deserialize
  error message.  See https://github.com/Pylons/colander/pull/41

0.9.6 (2012-02-14)
==================

- No longer runs on Python 2.4 or 2.5.  Python 2.6+ is now required.

- Python 3.2 compatibility.

- Removed a dependency on the iso8601 package (code from the package is now
  inlined in Colander itself).

- Added copyright and licensing information for iso8601-derived code to
  LICENSE.txt.

0.9.5 (2012-01-13)
==================

- Added Czech translation.

- Compile pt_BR translation (it was previously uncompiled).

- Minor docs fixes.

- Documentation added about flatten and unflatten.

0.9.4 (2011-10-14)
==================

- ``flatten`` now only includes leaf nodes in the flattened dict.

- ``flatten`` does not include a path element for the name of the type node
  for sequences.

- ``unflatten`` is implemented.

- Added ``__setitem__`` to ``SchemaNode``, allowing replacement of nodes by
  name.

- Added ``get_value`` and ``set_value`` methods to ``Schema`` which allow
  access and mutation of appstructs using dotted name paths.

- Add Swedish, French, Chinese translations.

0.9.3 (2011-06-23)
==================

- Add ``Time`` type.

- Add Dutch translation.

- Fix documentation: 0.9.2 requires ``deserialize`` of types to explicitly
  deal with the potential to receive ``colander.null``.

- Use ``default_tzinfo`` when deserializing naive datetimes.  See
  https://github.com/Pylons/colander/issues#issue/5.

- Allow ``default_tzinfo`` to be ``None`` when creating a
  ``colander.DateTime``.  See
  https://github.com/Pylons/colander/issues#issue/6.

- Add the ability to insert a ``colander.interfaces.Preparer`` between
  deserialization and validation. See the Preparing section in the
  documentation.

0.9.2 (2011-03-28)
==================

- Added Polish translation, thanks to Jedrzej Nowak.

- Moved to Pylons Project GitHub (https://github.com/Pylons/colander).

- Add tox.ini for testing purposes.

- New API: ``colander.required``.  Used as the marker value when a
  ``missing`` argument is left unspecified.

- Bug fix: if a ``title`` argument which is the empty string or ``None`` is
  passed explicitly to a SchemaNode, it is no longer replaced by a title
  computed from the name.

- Add SchemaNode.__contains__ to support "name in schema".

- SchemaNode deserialization now unconditionally calls the schema type's
  ``deserialize`` method to obtain an appstruct before attempting to
  validate.  Third party schema types should now return ``colander.null`` if
  passed a ``colander.null`` value or another logically "empty" value as a
  cstruct during ``deserialize``.

0.9.1 (2010-12-02)
==================

- When ``colander.null`` was unpickled, the reference created during
  unpickling was *not* a reference to the singleton but rather a new instance
  of the ``colander._null`` class.  This was unintentional, because lots of
  code checks for ``if x is colander.null``, which will fail across pickling
  and unpickling.  Now the reference created when ``colander.null`` is
  pickled is unpickled as the singleton itself.

0.9  (2010-11-28)
=================

- SchemaNode constructor now accepts arbitrary keyword arguments.  It
  sets any unknown values within the ``**kw`` sequence as attributes
  of the node object.

- Added Spanish locale:  thanks to Douglas Cerna for the translations!

- If you use a schema with deferred ``validator``, ``missing`` or
  ``default`` attributes, but you use it to perform serialization and
  deserialization without calling its ``bind`` method:

  - If ``validator`` is deferred, no validation will be performed.

  - If ``missing`` is deferred, the field will be considered *required*.

  - If ``default`` is deferred, the serialization default will be
    assumed to be ``colander.null``.

- Undocumented internal API for all type objects: ``flatten``.
  External type objects should now inherit from
  ``colander.SchemaType`` to get a default implementation.

0.8  (2010/09/08)
=================

- Docstring fixes to ``colander.SchemaNode`` (``missing`` is not the
  ``null`` value when required, it's a special marker value).

- The concept of "schema binding" was added, which allows for a more
  declarative-looking spelling of schemas and schema nodes which have
  dependencies on values available after the schema has already been
  fully constructed.  See the new narrative chapter in the
  documentation entitled "Schema Binding".

- The interface of ``colander.SchemaNode`` has grown a ``__delitem__``
  method.  The ``__iter__``, and ``__getitem__`` methods have now also
  been properly documented.

0.7.3 (2010/09/02)
==================

- The title of a schema node now defaults to a titleization of the
  ``name``.  Underscores in the ``name`` are replaced with empty
  strings and the first letter of every resulting word is capitalized.
  Previously the ``name`` was not split on underscores, and the
  entirety of the ``name`` was capitalized.

- A method of the ``colander.Invalid`` exception named ``messages``
  was added.  It returns an iterable of error messages using the
  ``msg`` attribute of its related exception node.  If the ``msg``
  attribute is iterable, it is returned.  If it is not iterable, a
  single-element list containing the ``msg`` value is returned.

0.7.2 (2010/08/30)
==================

- Add an ``colander.SchemaNode.__iter__`` method, which iterates over
  the children nodes of a schema node.

- The constructor of a ``colander.SchemaNode`` now accepts a
  ``widget`` keyword argument, for use by Deform (it is not used
  internally).

0.7.1 (2010/06/12)
==================

- Make it possible to use ``colander.null`` as a ``missing`` argument
  to ``colander.SchemaNode`` for roundtripping purposes.

- Make it possible to pickle ``colander.null``.

0.7.0
=====

A release centered around normalizing the treatment of default and
missing values.

Bug Fixes
---------

- Allow ``colander.Regex`` validator to accept a pattern object
  instead of just a string.

- Get rid of circular reference in Invalid exceptions: Invalid
  exceptions now no longer have a ``parent`` attribute.  Instead, they
  have a ``positional`` attribute, which signifies that the parent
  node type of the schema node to which they relate inherits from
  Positional.  This attribute isn't an API; it's used only internally
  for reporting.

- Raise a ``TypeError`` when bogus keyword arguments are passed to
  ``colander.SchemaNode``.

Backwards Incompatiblities / New Features
-----------------------------------------

- ``missing`` constructor arg to SchemaNode: signifies
  *deserialization* default, disambiguated from ``default`` which acted
  as both serialization and deserialization default previously.

  Changes necessitated / made possible by SchemaNode ``missing``
  addition:

  - The ``allow_empty`` argument of the ``colander.String`` type was
    removed (use ``missing=''`` as a wrapper SchemaNode argument
    instead).

- New concept: ``colander.null`` input to serialization and
  deserialization.  Use of ``colander.null`` normalizes serialization
  and deserialization default handling.

  Changes necessitated / made possible by ``colander.null`` addition:

  - ``partial`` argument and attribute of colander.MappingSchema has
     been removed; all serializations are partial, and partial
     deserializations are not necessary.

  - ``colander.null`` values are added to the cstruct for partial
     serializations instead of omitting missing node values from
     the cstruct.

  - ``colander.null`` may now be present in serialized and
     deserialized data structures.

  - ``sdefault`` attribute of SchemaNode has been removed; we never need
    to serialize a default anymore.

  - The value ``colander.null`` will be passed as ``appstruct`` to
    each type's ``serialize`` method when a mapping appstruct doesn't
    have a corresponding key instead of ``None``, as was the practice
    previously.

  - The value ``colander.null`` will be passed as ``cstruct`` to
    each type's ``deserialize`` method when a mapping cstruct
    doesn't have a corresponding key instead of ``None``, as was the
    practice previously.

  - Types now must handle ``colander.null`` explicitly during
    serialization.

- Updated and expanded documentation, particularly with respect to new
  ``colander.null`` handling.

- The ``value`` argument`` to the ``serialize`` method of a SchemaNode
  is now named ``appstruct``.  It is no longer a required argument; it
  defaults to ``colander.null`` now.

  The ``value`` argument to the ``deserialize`` method of a SchemaNode
  is now named ``cstruct``.  It is no longer a required argument; it
  defaults to ``colander.null`` now.

- The ``value`` argument to the ``serialize`` method of each built-in
  type is now named ``appstruct``, and is now required: it is no
  longer a keyword argument that has a default.

  The ``value`` argument to the ``deserialize`` method of each
  built-in type is now named ``cstruct``, and is now required: it is
  no longer a keyword argument that has a default.

0.6.2 (2010-05-08)
==================

- The default ``encoding`` parameter value to the ``colander.String``
  type is still ``None``, however its meaning has changed.  An
  encoding of ``None`` now means that no special encoding and decoding
  of Unicode values is done by the String type.  This differs from the
  previous behavior, where ``None`` implied that the encoding was
  ``utf-8``.  Pass the encoding as ``utf-8`` specifically to get the
  older behavior back.  This is in support of Deform.

- The default ``err_template`` value attached to the ``colander.Date``
  and ``colander.Datetime`` types was changed.  It is now simply
  ``Invalid date`` instead of ``_('${val} cannot be parsed as an
  iso8601 date: ${err}')``.  This is in support of Deform.

- Fix bug in ``colander.Boolean`` that attempted to call ``.lower`` on
  a bool value when a default value was found for the schema node.

0.6.1 (2010-05-04)
==================

- Add a Decimal type (number type which uses ``decimal.Decimal`` as a
  deserialization target).

0.6.0 (2010-05-02)
==================

- (Hopefully) fix intermittent datetime-granularity-related test
  failures.

- Internationalized error messages.  This required some changes to
  error message formatting, which may impact you if you were feeding
  colander an error message template.

- New project dependency: ``translationstring`` package for
  internationalization.

- New argument to ``colander.String`` constructor: ``allow_empty``.
  This is a boolean representing whether an empty string is a valid
  value during deserialization, defaulting to ``False``.

- Add minimal documentation about the composition of a
  colander.Invalid exception to the narrative docs.

- Add (existing, but previously non-API) colander.Invalid attributes
  to its interface within the API documentation.

0.5.2 (2010-04-09)
==================

- Add Email and Regex validators (courtesy Steve Howe).

- Raise a ``colander.Invalid`` error if a ``colander.SequenceSchema``
  is created with more than one member.

- Add ``Function`` validator.

- Fix bug in serialization of non-Unicode values in the ``String`` class.

- Get rid of ``pserialize`` in favor of making ``serialize`` always
  partially serialize.

- Get rid of ``pdeserialize``: it existed only for symmetry.  We'll
  add something like it back later if we need it.

0.5.1 (2010-04-02)
==================

- The constructor arguments to a the ``colander.Schema`` class are now
  sent to the constructed SchemaNode rather than to the type it represents.

- Allow ``colander.Date`` and ``colander.DateTime`` invalid error
  messages to be customized.

- Add a ``pos`` argument to the ``colander.Invalid.add`` method.

- Add a ``__setitem__`` method to the ``colander.Invalid`` class.

- The ``colander.Mapping`` constructor keyword argument
  ``unknown_keys`` has been renamed to ``unknown``.

- Allow ``colander.Mapping`` type to accept a new constructor
  argument: ``partial``.

- New interface methods required by types and schema nodes:
  ``pserialize`` and ``pdeserialize``.  These partially serialize or
  partially deserialize a value (the definition of "partial" is up to
  the type).

0.5 (2010-03-31)
================

- 0.4 was mispackaged (CHANGES.txt missing); no code changes from 0.4
  however.

0.4 (2010-03-30)
================

- Add ``colander.DateTime`` and ``colander.Date`` data types.

- Depend on the ``iso8601`` package for date support.

0.3 (2010-03-29)
================

- Subnodes of a schema node are now kept in the ``children`` attribute
  rather than the ``nodes`` attribute.

- Add an ``sdefault`` property to ``colander.SchemaNode`` objects.

- Add a ``clone`` method to ``colander.SchemaNode`` objects.

- Add a ``__str__`` method to the ``colander.Invalid`` exception that
  prints an error summary.

- Various error message improvements.

- Add ``colander.Length`` validator class.

0.2 (2010-03-23)
================

- Make nodetype overrideable.

- Add __getitem__ to SchemaNode.

- Fix OneOf message.

- Capitalize node titles.

- Deal with empty strings in String, Boolean, and Float types.

- Introduce description; make title the same as name.

- Remove copy method from schemanode.

- Allow schema nodes to have titles.

- The term "structure" is too overloaded to use for schema purposes:
  structure -> schema node.

- Make Sequence more like Tuple and Mapping (it uses a substructure
  rather than a structure parameter to denote its type).

- Add __repr__ and copy methods to structure.

- Add accept_scalar flag to Sequence.


0.1 (2010-03-14)
================

- Initial release.


