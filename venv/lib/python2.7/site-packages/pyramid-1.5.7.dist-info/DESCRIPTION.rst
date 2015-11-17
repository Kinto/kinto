Pyramid
=======

.. image:: https://travis-ci.org/Pylons/pyramid.png?branch=1.5-branch
        :target: https://travis-ci.org/Pylons/pyramid

.. image:: https://readthedocs.org/projects/pyramid/badge/?version=latest
        :target: http://docs.pylonsproject.org/projects/pyramid/en/latest/
        :alt: Documentation Status

Pyramid is a small, fast, down-to-earth, open source Python web framework.
It makes real-world web application development and
deployment more fun, more predictable, and more productive.

Pyramid is produced by the `Pylons Project <http://pylonsproject.org/>`_.

Support and Documentation
-------------------------

See the `Pylons Project website <http://pylonsproject.org/>`_ to view
documentation, report bugs, and obtain support.

License
-------

Pyramid is offered under the BSD-derived `Repoze Public License
<http://repoze.org/license.html>`_.

Authors
-------

Pyramid is made available by `Agendaless Consulting <http://agendaless.com>`_
and a team of contributors.



.. _changes_1.5.7:

1.5.7 (2015-04-28)
==================

- Further fix the JSONP renderer by prefixing the returned content with
  a comment. This should mitigate attacks from Flash (See CVE-2014-4671).
  See https://github.com/Pylons/pyramid/pull/1648

- Allow periods and brackets (``[]``) in the JSONP callback. The original
  fix was overly-restrictive and broke Angular.
  See https://github.com/Pylons/pyramid/pull/1648

.. _changes_1.5.6:

1.5.6 (2015-04-14)
==================

- 1.5.5 was a brown-bag release which was missing files.

.. _changes_1.5.5:

1.5.5 (2015-04-14)
==================

- The JSONP renderer created JavaScript code in such a way that a callback
  variable could be used to arbitrarily inject javascript into the response
  object. https://github.com/Pylons/pyramid/pull/1626

.. _changes_1.5.4:

1.5.4 (2015-02-24)
==================

- Fix regression where ``pserve --reload`` would not work when running
  as a daemon.
  Backported from https://github.com/Pylons/pyramid/pull/1592

.. _changes_1.5.3:

1.5.3 (2015-02-22)
==================

- Work around an issue where ``pserve --reload`` would leave terminal echo
  disabled if it reloaded during a pdb session.
  Backported from https://github.com/Pylons/pyramid/pull/1577

- Fixed a failing unittest caused by differing mimetypes on various
  OS platforms. See https://github.com/Pylons/pyramid/issues/1405

- Overall improvments for the ``proutes`` command. Added ``--format`` and
  ``--glob`` arguments to the command, introduced the ``method``
  column for displaying available request methods, and improved the ``view``
  output by showing the module instead of just ``__repr__``.
  See: https://github.com/Pylons/pyramid/pull/1542

- The ``pyramid.renderers.JSONP`` renderer would raise an exception if used
  without a request object. It will now fallback to behave like
  the ``pyramid.renderers.JSON`` renderer if there is no request object to
  derive a callback from. See https://github.com/Pylons/pyramid/pull/1562

- Prevent "parameters to load are deprecated" ``DeprecationWarning``
  from setuptools>=11.3. See https://github.com/Pylons/pyramid/pull/1541

- Avoiding timing attacks against CSRF tokens. Backported from
  https://github.com/Pylons/pyramid/pull/1574

- ``pserve`` can now take a ``-b`` or ``--browser`` option to open the server
  URL in a web browser. See https://github.com/Pylons/pyramid/pull/1533

.. _changes_1.5.2:

1.5.2 (2014-11-09)
==================

Bug Fixes
---------

- ``pyramid.wsgi.wsgiapp`` and ``pyramid.wsgi.wsgiapp2`` now raise
  ``ValueError`` when accidentally passed ``None``.
  See https://github.com/Pylons/pyramid/pull/1320

- Work around a bug introduced in Python 2.7.7 on Windows where
  ``mimetypes.guess_type`` returns Unicode rather than str for the content
  type, unlike any previous version of Python.  See
  https://github.com/Pylons/pyramid/issues/1360 for more information.

Docs
----

- Removed logging configuration from Quick Tutorial ini files except for
  scaffolding- and logging-related chapters to avoid needing to explain it too
  early.

- Clarify a previously-implied detail of the ``ISession.invalidate`` API
  documentation.

.. _changes_1.5.1:

1.5.1 (2014-05-31)
==================

- Update scaffold generating machinery to return the version of pyramid and
  pyramid docs for use in scaffolds. Updated starter, alchemy and zodb
  templates to have links to correctly versioned documentation and reflect
  which pyramid was used to generate the scaffold.

- Fix an issue whereby predicates would be resolved as maybe_dotted in the
  introspectable but not when passed for registration. This would mean that
  ``add_route_predicate`` for example can not take a string and turn it into
  the actual callable function.
  See https://github.com/Pylons/pyramid/pull/1306

- Fix ``pyramid.testing.setUp`` to return a ``Configurator`` with a proper
  package. Previously it was not possible to do package-relative includes
  using the returned ``Configurator`` during testing. There is now a
  ``package`` argument that can override this behavior as well.
  See https://github.com/Pylons/pyramid/pull/1322

- Removed non-ascii copyright symbol from templates, as this was
  causing the scaffolds to fail for project generation on some systems.

- Fix an issue where a ``pyramid.response.FileResponse`` may apply a charset
  where it does not belong. See https://github.com/Pylons/pyramid/pull/1251

.. _changes_1.5:

1.5 (2014-04-08)
================

- Avoid crash in ``pserve --reload`` under Py3k, when iterating over possibly
  mutated ``sys.modules``.

- ``UnencryptedCookieSessionFactoryConfig`` failed if the secret contained
  higher order characters. See https://github.com/Pylons/pyramid/issues/1246

- Fixed a bug in ``UnencryptedCookieSessionFactoryConfig`` and
  ``SignedCookieSessionFactory`` where ``timeout=None`` would cause a new
  session to always be created. Also in ``SignedCookieSessionFactory`` a
  ``reissue_time=None`` would cause an exception when modifying the session.
  See https://github.com/Pylons/pyramid/issues/1247

- Updated docs and scaffolds to keep in step with new 2.0 release of
  ``Lingua``.  This included removing all ``setup.cfg`` files from scaffolds
  and documentation environments.

1.5b1 (2014-02-08)
==================

Features
--------

- We no longer eagerly clear ``request.exception`` and ``request.exc_info`` in
  the exception view tween.  This makes it possible to inspect exception
  information within a finished callback.  See
  https://github.com/Pylons/pyramid/issues/1223.

1.5a4 (2014-01-28)
==================

Features
--------

- Updated scaffolds with new theme, fixed documentation and sample project.

Bug Fixes
---------

- Depend on a newer version of WebOb so that we pull in some crucial bug-fixes
  that were showstoppers for functionality in Pyramid.

- Add a trailing semicolon to the JSONP response. This fixes JavaScript syntax
  errors for old IE versions. See https://github.com/Pylons/pyramid/pull/1205

- Fix a memory leak when the configurator's ``set_request_property`` method was
  used or when the configurator's ``add_request_method`` method was used with
  the ``property=True`` attribute.  See
  https://github.com/Pylons/pyramid/issues/1212 .

1.5a3 (2013-12-10)
==================

Features
--------

- An authorization API has been added as a method of the
  request: ``request.has_permission``.

  ``request.has_permission`` is a method-based alternative to the
  ``pyramid.security.has_permission`` API and works exactly the same.  The
  older API is now deprecated.

- Property API attributes have been added to the request for easier access to
  authentication data: ``request.authenticated_userid``,
  ``request.unauthenticated_userid``, and ``request.effective_principals``.

  These are analogues, respectively, of
  ``pyramid.security.authenticated_userid``,
  ``pyramid.security.unauthenticated_userid``, and
  ``pyramid.security.effective_principals``.  They operate exactly the same,
  except they are attributes of the request instead of functions accepting a
  request.  They are properties, so they cannot be assigned to.  The older
  function-based APIs are now deprecated.

- Pyramid's console scripts (``pserve``, ``pviews``, etc) can now be run
  directly, allowing custom arguments to be sent to the python interpreter
  at runtime. For example::

      python -3 -m pyramid.scripts.pserve development.ini

- Added a specific subclass of ``HTTPBadRequest`` named
  ``pyramid.exceptions.BadCSRFToken`` which will now be raised in response
  to failures in ``check_csrf_token``.
  See https://github.com/Pylons/pyramid/pull/1149

- Added a new ``SignedCookieSessionFactory`` which is very similar to the
  ``UnencryptedCookieSessionFactoryConfig`` but with a clearer focus on signing
  content. The custom serializer arguments to this function should only focus
  on serializing, unlike its predecessor which required the serializer to also
  perform signing.  See https://github.com/Pylons/pyramid/pull/1142 .  Note
  that cookies generated using ``SignedCookieSessionFactory`` are not
  compatible with cookies generated using ``UnencryptedCookieSessionFactory``,
  so existing user session data will be destroyed if you switch to it.

- Added a new ``BaseCookieSessionFactory`` which acts as a generic cookie
  factory that can be used by framework implementors to create their own
  session implementations. It provides a reusable API which focuses strictly
  on providing a dictionary-like object that properly handles renewals,
  timeouts, and conformance with the ``ISession`` API.
  See https://github.com/Pylons/pyramid/pull/1142

- The anchor argument to ``pyramid.request.Request.route_url`` and
  ``pyramid.request.Request.resource_url`` and their derivatives will now be
  escaped via URL quoting to ensure minimal conformance.  See
  https://github.com/Pylons/pyramid/pull/1183

- Allow sending of ``_query`` and ``_anchor`` options to
  ``pyramid.request.Request.static_url`` when an external URL is being
  generated.
  See https://github.com/Pylons/pyramid/pull/1183

- You can now send a string as the ``_query`` argument to
  ``pyramid.request.Request.route_url`` and
  ``pyramid.request.Request.resource_url`` and their derivatives.  When a
  string is sent instead of a list or dictionary. it is URL-quoted however it
  does not need to be in ``k=v`` form.  This is useful if you want to be able
  to use a different query string format than ``x-www-form-urlencoded``.  See
  https://github.com/Pylons/pyramid/pull/1183

- ``pyramid.testing.DummyRequest`` now has a ``domain`` attribute to match the
  new WebOb 1.3 API.  Its value is ``example.com``.

Bug Fixes
---------

- Fix the ``pcreate`` script so that when the target directory name ends with a
  slash it does not produce a non-working project directory structure.
  Previously saying ``pcreate -s starter /foo/bar/`` produced different output
  than  saying ``pcreate -s starter /foo/bar``.  The former did not work
  properly.

- Fix the ``principals_allowed_by_permission`` method of
  ``ACLAuthorizationPolicy`` so it anticipates a callable ``__acl__``
  on resources.  Previously it did not try to call the ``__acl__``
  if it was callable.

- The ``pviews`` script did not work when a url required custom request
  methods in order to perform traversal. Custom methods and descriptors added
  via ``pyramid.config.Configurator.add_request_method`` will now be present,
  allowing traversal to continue.
  See https://github.com/Pylons/pyramid/issues/1104

- Remove unused ``renderer`` argument from ``Configurator.add_route``.

- Allow the ``BasicAuthenticationPolicy`` to work with non-ascii usernames
  and passwords. The charset is not passed as part of the header and different
  browsers alternate between UTF-8 and Latin-1, so the policy now attempts
  to decode with UTF-8 first, and will fallback to Latin-1.
  See https://github.com/Pylons/pyramid/pull/1170

- The ``@view_defaults`` now apply to notfound and forbidden views
  that are defined as methods of a decorated class.
  See https://github.com/Pylons/pyramid/issues/1173

Documentation
-------------

- Added a "Quick Tutorial" to go with the Quick Tour

- Removed mention of ``pyramid_beaker`` from docs.  Beaker is no longer
  maintained.  Point people at ``pyramid_redis_sessions`` instead.

- Add documentation for ``pyramid.interfaces.IRendererFactory`` and
  ``pyramid.interfaces.IRenderer``.

Backwards Incompatibilities
---------------------------

- The key/values in the ``_query`` parameter of ``request.route_url`` and the
  ``query`` parameter of ``request.resource_url`` (and their variants), used
  to encode a value of ``None`` as the string ``'None'``, leaving the resulting
  query string to be ``a=b&key=None``. The value is now dropped in this
  situation, leaving a query string of ``a=b&key=``.
  See https://github.com/Pylons/pyramid/issues/1119

Deprecations
------------

- Deprecate the ``pyramid.interfaces.ITemplateRenderer`` interface. It was
  ill-defined and became unused when Mako and Chameleon template bindings were
  split into their own packages.

- The ``pyramid.session.UnencryptedCookieSessionFactoryConfig`` API has been
  deprecated and is superseded by the
  ``pyramid.session.SignedCookieSessionFactory``.  Note that while the cookies
  generated by the ``UnencryptedCookieSessionFactoryConfig``
  are compatible with cookies generated by old releases, cookies generated by
  the SignedCookieSessionFactory are not. See
  https://github.com/Pylons/pyramid/pull/1142

- The ``pyramid.security.has_permission`` API is now deprecated.  Instead, use
  the newly-added ``has_permission`` method of the request object.

- The ``pyramid.security.effective_principals`` API is now deprecated.
  Instead, use the newly-added ``effective_principals`` attribute of the
  request object.

- The ``pyramid.security.authenticated_userid`` API is now deprecated.
  Instead, use the newly-added ``authenticated_userid`` attribute of the
  request object.

- The ``pyramid.security.unauthenticated_userid`` API is now deprecated.
  Instead, use the newly-added ``unauthenticated_userid`` attribute of the
  request object.

Dependencies
------------

- Pyramid now depends on WebOb>=1.3 (it uses ``webob.cookies.CookieProfile``
  from 1.3+).

1.5a2 (2013-09-22)
==================

Features
--------

- Users can now provide dotted Python names to as the ``factory`` argument
  the Configurator methods named ``add_{view,route,subscriber}_predicate``
  (instead of passing the predicate factory directly, you can pass a
  dotted name which refers to the factory).

Bug Fixes
---------

- Fix an exception in ``pyramid.path.package_name`` when resolving the package
  name for namespace packages that had no ``__file__`` attribute.

Backwards Incompatibilities
---------------------------

- Pyramid no longer depends on or configures the Mako and Chameleon templating
  system renderers by default.  Disincluding these templating systems by
  default means that the Pyramid core has fewer dependencies and can run on
  future platforms without immediate concern for the compatibility of its
  templating add-ons.  It also makes maintenance slightly more effective, as
  different people can maintain the templating system add-ons that they
  understand and care about without needing commit access to the Pyramid core,
  and it allows users who just don't want to see any packages they don't use
  come along for the ride when they install Pyramid.

  This means that upon upgrading to Pyramid 1.5a2+, projects that use either
  of these templating systems will see a traceback that ends something like
  this when their application attempts to render a Chameleon or Mako template::

     ValueError: No such renderer factory .pt

  Or::

     ValueError: No such renderer factory .mako

  Or::

     ValueError: No such renderer factory .mak

  Support for Mako templating has been moved into an add-on package named
  ``pyramid_mako``, and support for Chameleon templating has been moved into
  an add-on package named ``pyramid_chameleon``.  These packages are drop-in
  replacements for the old built-in support for these templating langauges.
  All you have to do is install them and make them active in your configuration
  to register renderer factories for ``.pt`` and/or ``.mako`` (or ``.mak``) to
  make your application work again.

  To re-add support for Chameleon and/or Mako template renderers into your
  existing projects, follow the below steps.

  If you depend on Mako templates:

  * Make sure the ``pyramid_mako`` package is installed.  One way to do this
    is by adding ``pyramid_mako`` to the ``install_requires`` section of your
    package's ``setup.py`` file and afterwards rerunning ``setup.py develop``::

        setup(
            #...
            install_requires=[
                'pyramid_mako',         # new dependency
                'pyramid',
                #...
            ],
        )

  * Within the portion of your application which instantiates a Pyramid
    ``pyramid.config.Configurator`` (often the ``main()`` function in
    your project's ``__init__.py`` file), tell Pyramid to include the
    ``pyramid_mako`` includeme::

        config = Configurator(.....)
        config.include('pyramid_mako')

  If you depend on Chameleon templates:

  * Make sure the ``pyramid_chameleon`` package is installed.  One way to do
    this is by adding ``pyramid_chameleon`` to the ``install_requires`` section
    of your package's ``setup.py`` file and afterwards rerunning
    ``setup.py develop``::

        setup(
            #...
            install_requires=[
                'pyramid_chameleon',         # new dependency
                'pyramid',
                #...
            ],
        )

  * Within the portion of your application which instantiates a Pyramid
    ``~pyramid.config.Configurator`` (often the ``main()`` function in
    your project's ``__init__.py`` file), tell Pyramid to include the
    ``pyramid_chameleon`` includeme::

        config = Configurator(.....)
        config.include('pyramid_chameleon')

  Note that it's also fine to install these packages into *older* Pyramids for
  forward compatibility purposes.  Even if you don't upgrade to Pyramid 1.5
  immediately, performing the above steps in a Pyramid 1.4 installation is
  perfectly fine, won't cause any difference, and will give you forward
  compatibility when you eventually do upgrade to Pyramid 1.5.

  With the removal of Mako and Chameleon support from the core, some
  unit tests that use the ``pyramid.renderers.render*`` methods may begin to
  fail.  If any of your unit tests are invoking either
  ``pyramid.renderers.render()``  or ``pyramid.renderers.render_to_response()``
  with either Mako or Chameleon templates then the
  ``pyramid.config.Configurator`` instance in effect during
  the unit test should be also be updated to include the addons, as shown
  above. For example::

        class ATest(unittest.TestCase):
            def setUp(self):
                self.config = pyramid.testing.setUp()
                self.config.include('pyramid_mako')

            def test_it(self):
                result = pyramid.renderers.render('mypkg:templates/home.mako', {})

  Or::

        class ATest(unittest.TestCase):
            def setUp(self):
                self.config = pyramid.testing.setUp()
                self.config.include('pyramid_chameleon')

            def test_it(self):
                result = pyramid.renderers.render('mypkg:templates/home.pt', {})

- If you're using the Pyramid debug toolbar, when you upgrade Pyramid to
  1.5a2+, you'll also need to upgrade the ``pyramid_debugtoolbar`` package to
  at least version 1.0.8, as older toolbar versions are not compatible with
  Pyramid 1.5a2+ due to the removal of Mako support from the core.  It's
  fine to use this newer version of the toolbar code with older Pyramids too.

- Removed the ``request.response_*`` varying attributes. These attributes
  have been deprecated since Pyramid 1.1, and as per the deprecation policy,
  have now been removed.

- ``request.response`` will no longer be mutated when using the
  ``pyramid.renderers.render()`` API.  Almost all renderers mutate the
  ``request.response`` response object (for example, the JSON renderer sets
  ``request.response.content_type`` to ``application/json``), but this is
  only necessary when the renderer is generating a response; it was a bug
  when it was done as a side effect of calling ``pyramid.renderers.render()``.

- Removed the ``bfg2pyramid`` fixer script.

- The ``pyramid.events.NewResponse`` event is now sent **after** response
  callbacks are executed.  It previously executed before response callbacks
  were executed.  Rationale: it's more useful to be able to inspect the response
  after response callbacks have done their jobs instead of before.

- Removed the class named ``pyramid.view.static`` that had been deprecated
  since Pyramid 1.1.  Instead use ``pyramid.static.static_view`` with
  ``use_subpath=True`` argument.

- Removed the ``pyramid.view.is_response`` function that had been deprecated
  since Pyramid 1.1.  Use the ``pyramid.request.Request.is_response`` method
  instead.

- Removed the ability to pass the following arguments to
  ``pyramid.config.Configurator.add_route``: ``view``, ``view_context``.
  ``view_for``, ``view_permission``, ``view_renderer``, and ``view_attr``.
  Using these arguments had been deprecated since Pyramid 1.1.  Instead of
  passing view-related arguments to ``add_route``, use a separate call to
  ``pyramid.config.Configurator.add_view`` to associate a view with a route
  using its ``route_name`` argument.  Note that this impacts the
  ``pyramid.config.Configurator.add_static_view`` function too, because it
  delegates to ``add_route``.

- Removed the ability to influence and query a ``pyramid.request.Request``
  object as if it were a dictionary.  Previously it was possible to use methods
  like ``__getitem__``, ``get``, ``items``, and other dictlike methods to
  access values in the WSGI environment.  This behavior had been deprecated
  since Pyramid 1.1.  Use methods of ``request.environ`` (a real dictionary)
  instead.

- Removed ancient backwards compatibily hack in
  ``pyramid.traversal.DefaultRootFactory`` which populated the ``__dict__`` of
  the factory with the matchdict values for compatibility with BFG 0.9.

- The ``renderer_globals_factory`` argument to the
  ``pyramid.config.Configurator` constructor and its ``setup_registry`` method
  has been removed.  The ``set_renderer_globals_factory`` method of
  ``pyramid.config.Configurator`` has also been removed.  The (internal)
  ``pyramid.interfaces.IRendererGlobals`` interface was also removed.  These
  arguments, methods and interfaces had been deprecated since 1.1.  Use a
  ``BeforeRender`` event subscriber as documented in the "Hooks" chapter of the
  Pyramid narrative documentation instead of providing renderer globals values
  to the configurator.

Deprecations
------------

- The ``pyramid.config.Configurator.set_request_property`` method now issues
  a deprecation warning when used.  It had been docs-deprecated in 1.4
  but did not issue a deprecation warning when used.

1.5a1 (2013-08-30)
==================

Features
--------

- A new http exception subclass named ``pyramid.httpexceptions.HTTPSuccessful``
  was added.  You can use this class as the ``context`` of an exception
  view to catch all 200-series "exceptions" (e.g. "raise HTTPOk").  This
  also allows you to catch *only* the ``HTTPOk`` exception itself; previously
  this was impossible because a number of other exceptions
  (such as ``HTTPNoContent``) inherited from ``HTTPOk``, but now they do not.

- You can now generate "hybrid" urldispatch/traversal URLs more easily
  by using the new ``route_name``, ``route_kw`` and ``route_remainder_name``
  arguments to  ``request.resource_url`` and ``request.resource_path``.  See
  the new section of the "Combining Traversal and URL Dispatch" documentation
  chapter entitled  "Hybrid URL Generation".

- It is now possible to escape double braces in Pyramid scaffolds (unescaped,
  these represent replacement values).  You can use ``\{\{a\}\}`` to
  represent a "bare" ``{{a}}``.  See
  https://github.com/Pylons/pyramid/pull/862

- Add ``localizer`` and ``locale_name`` properties (reified) to the request.
  See https://github.com/Pylons/pyramid/issues/508.  Note that the
  ``pyramid.i18n.get_localizer`` and ``pyramid.i18n.get_locale_name`` functions
  now simply look up these properties on the request.

- Add ``pdistreport`` script, which prints the Python version in use, the
  Pyramid version in use, and the version number and location of all Python
  distributions currently installed.

- Add the ability to invert the result of any view, route, or subscriber
  predicate using the ``not_`` class.  For example::

     from pyramid.config import not_

     @view_config(route_name='myroute', request_method=not_('POST'))
     def myview(request): ...

  The above example will ensure that the view is called if the request method
  is not POST (at least if no other view is more specific).

  The ``pyramid.config.not_`` class can be used against any value that is
  a predicate value passed in any of these contexts:

  - ``pyramid.config.Configurator.add_view``

  - ``pyramid.config.Configurator.add_route``

  - ``pyramid.config.Configurator.add_subscriber``

  - ``pyramid.view.view_config``

  - ``pyramid.events.subscriber``

- ``scripts/prequest.py``: add support for submitting ``PUT`` and ``PATCH``
  requests.  See https://github.com/Pylons/pyramid/pull/1033.  add support for
  submitting ``OPTIONS`` and ``PROPFIND`` requests, and  allow users to specify
  basic authentication credentials in the request via a ``--login`` argument to
  the script.  See https://github.com/Pylons/pyramid/pull/1039.

- ``ACLAuthorizationPolicy`` supports ``__acl__`` as a callable. This
  removes the ambiguity between the potential ``AttributeError`` that would
  be raised on the ``context`` when the property was not defined and the
  ``AttributeError`` that could be raised from any user-defined code within
  a dynamic property. It is recommended to define a dynamic ACL as a callable
  to avoid this ambiguity. See https://github.com/Pylons/pyramid/issues/735.

- Allow a protocol-relative URL (e.g. ``//example.com/images``) to be passed to
  ``pyramid.config.Configurator.add_static_view``. This allows
  externally-hosted static URLs to be generated based on the current protocol.

- The ``AuthTktAuthenticationPolicy`` has two new options to configure its
  domain usage:

  * ``parent_domain``: if set the authentication cookie is set on
    the parent domain. This is useful if you have multiple sites sharing the
    same domain.
  * ``domain``: if provided the cookie is always set for this domain, bypassing
    all usual logic.

  See https://github.com/Pylons/pyramid/pull/1028,
  https://github.com/Pylons/pyramid/pull/1072 and
  https://github.com/Pylons/pyramid/pull/1078.

- The ``AuthTktAuthenticationPolicy`` now supports IPv6 addresses when using
  the ``include_ip=True`` option. This is possibly incompatible with
  alternative ``auth_tkt`` implementations, as the specification does not
  define how to properly handle IPv6. See
  https://github.com/Pylons/pyramid/issues/831.

- Make it possible to use variable arguments via
  ``pyramid.paster.get_appsettings``. This also allowed the generated
  ``initialize_db`` script from the ``alchemy`` scaffold to grow support
  for options in the form ``a=1 b=2`` so you can fill in
  values in a parameterized ``.ini`` file, e.g.
  ``initialize_myapp_db etc/development.ini a=1 b=2``.
  See https://github.com/Pylons/pyramid/pull/911

- The ``request.session.check_csrf_token()`` method and the ``check_csrf`` view
  predicate now take into account the value of the HTTP header named
  ``X-CSRF-Token`` (as well as the ``csrf_token`` form parameter, which they
  always did).  The header is tried when the form parameter does not exist.

- View lookup will now search for valid views based on the inheritance
  hierarchy of the context. It tries to find views based on the most
  specific context first, and upon predicate failure, will move up the
  inheritance chain to test views found by the super-type of the context.
  In the past, only the most specific type containing views would be checked
  and if no matching view could be found then a PredicateMismatch would be
  raised. Now predicate mismatches don't hide valid views registered on
  super-types. Here's an example that now works::

     class IResource(Interface):

         ...

     @view_config(context=IResource)
     def get(context, request):

         ...

     @view_config(context=IResource, request_method='POST')
     def post(context, request):

         ...

     @view_config(context=IResource, request_method='DELETE')
     def delete(context, request):

         ...

     @implementer(IResource)
     class MyResource:

         ...

     @view_config(context=MyResource, request_method='POST')
     def override_post(context, request):

         ...

  Previously the override_post view registration would hide the get
  and delete views in the context of MyResource -- leading to a
  predicate mismatch error when trying to use GET or DELETE
  methods. Now the views are found and no predicate mismatch is
  raised.
  See https://github.com/Pylons/pyramid/pull/786 and
  https://github.com/Pylons/pyramid/pull/1004 and
  https://github.com/Pylons/pyramid/pull/1046

- The ``pserve`` command now takes a ``-v`` (or ``--verbose``) flag and a
  ``-q`` (or ``--quiet``) flag.  Output from running ``pserve`` can be
  controlled using these flags.  ``-v`` can be specified multiple times to
  increase verbosity.  ``-q`` sets verbosity to ``0`` unconditionally.  The
  default verbosity level is ``1``.

- The ``alchemy`` scaffold tests now provide better coverage.  See
  https://github.com/Pylons/pyramid/pull/1029

- The ``pyramid.config.Configurator.add_route`` method now supports being
  called with an external URL as pattern. See
  https://github.com/Pylons/pyramid/issues/611 and the documentation section
  in the "URL Dispatch" chapter entitled "External Routes" for more information.

Bug Fixes
---------

- It was not possible to use ``pyramid.httpexceptions.HTTPException`` as
  the ``context`` of an exception view as very general catchall for
  http-related exceptions when you wanted that exception view to override the
  default exception view.  See https://github.com/Pylons/pyramid/issues/985

- When the ``pyramid.reload_templates`` setting was true, and a Chameleon
  template was reloaded, and the renderer specification named a macro
  (e.g. ``foo#macroname.pt``), renderings of the template after the template
  was reloaded due to a file change would produce the entire template body
  instead of just a rendering of the macro.  See
  https://github.com/Pylons/pyramid/issues/1013.

- Fix an obscure problem when combining a virtual root with a route with a
  ``*traverse`` in its pattern.  Now the traversal path generated in
  such a configuration will be correct, instead of an element missing
  a leading slash.

- Fixed a Mako renderer bug returning a tuple with a previous defname value
  in some circumstances. See https://github.com/Pylons/pyramid/issues/1037
  for more information.

- Make the ``pyramid.config.assets.PackageOverrides`` object implement the API
  for ``__loader__`` objects specified in PEP 302.  Proxies to the
  ``__loader__`` set by the importer, if present; otherwise, raises
  ``NotImplementedError``.  This makes Pyramid static view overrides work
  properly under Python 3.3 (previously they would not).  See
  https://github.com/Pylons/pyramid/pull/1015 for more information.

- ``mako_templating``: added defensive workaround for non-importability of
  ``mako`` due to upstream ``markupsafe`` dropping Python 3.2 support.  Mako
  templating will no longer work under the combination of MarkupSafe 0.17 and
  Python 3.2 (although the combination of MarkupSafe 0.17 and Python 3.3 or any
  supported Python 2 version will work OK).

- Spaces and dots may now be in mako renderer template paths. This was
  broken when support for the new makodef syntax was added in 1.4a1.
  See https://github.com/Pylons/pyramid/issues/950

- ``pyramid.debug_authorization=true`` will now correctly print out
  ``Allowed`` for views registered with ``NO_PERMISSION_REQUIRED`` instead
  of invoking the ``permits`` method of the authorization policy.
  See https://github.com/Pylons/pyramid/issues/954

- Pyramid failed to install on some systems due to being packaged with
  some test files containing higher order characters in their names. These
  files have now been removed. See
  https://github.com/Pylons/pyramid/issues/981

- ``pyramid.testing.DummyResource`` didn't define ``__bool__``, so code under
  Python 3 would use ``__len__`` to find truthiness; this usually caused an
  instance of DummyResource to be "falsy" instead of "truthy".  See
  https://github.com/Pylons/pyramid/pull/1032

- The ``alchemy`` scaffold would break when the database was MySQL during
  tables creation.  See https://github.com/Pylons/pyramid/pull/1049

- The ``current_route_url`` method now attaches the query string to the URL by
  default. See
  https://github.com/Pylons/pyramid/issues/1040

- Make ``pserve.cherrypy_server_runner`` Python 3 compatible. See
  https://github.com/Pylons/pyramid/issues/718

Backwards Incompatibilities
---------------------------

- Modified the ``current_route_url`` method in pyramid.Request. The method
  previously returned the URL without the query string by default, it now does
  attach the query string unless it is overriden.

- The ``route_url`` and ``route_path`` APIs no longer quote ``/``
  to ``%2F`` when a replacement value contains a ``/``.  This was pointless,
  as WSGI servers always unquote the slash anyway, and Pyramid never sees the
  quoted value.

- It is no longer possible to set a ``locale_name`` attribute of the request,
  nor is it possible to set a ``localizer`` attribute of the request.  These
  are now "reified" properties that look up a locale name and localizer
  respectively using the machinery described in the "Internationalization"
  chapter of the documentation.

- If you send an ``X-Vhm-Root`` header with a value that ends with a slash (or
  any number of slashes), the trailing slash(es) will be removed before a URL
  is generated when you use use ``request.resource_url`` or
  ``request.resource_path``.  Previously the virtual root path would not have
  trailing slashes stripped, which would influence URL generation.

- The ``pyramid.interfaces.IResourceURL`` interface has now grown two new
  attributes: ``virtual_path_tuple`` and ``physical_path_tuple``.  These should
  be the tuple form of the resource's path (physical and virtual).



