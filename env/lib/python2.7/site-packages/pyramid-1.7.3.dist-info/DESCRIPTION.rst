Pyramid
=======

.. image:: https://travis-ci.org/Pylons/pyramid.png?branch=1.7-branch
        :target: https://travis-ci.org/Pylons/pyramid
        :alt: 1.7-branch Travis CI Status

.. image:: https://readthedocs.org/projects/pyramid/badge/?version=master
        :target: http://docs.pylonsproject.org/projects/pyramid/en/master/
        :alt: Master Documentation Status

.. image:: https://readthedocs.org/projects/pyramid/badge/?version=latest
        :target: http://docs.pylonsproject.org/projects/pyramid/en/latest/
        :alt: Latest Documentation Status

.. image:: https://img.shields.io/badge/irc-freenode-blue.svg
        :target: https://webchat.freenode.net/?channels=pyramid
        :alt: IRC Freenode

`Pyramid <https://trypyramid.com/>`_ is a small, fast, down-to-earth, open
source Python web framework. It makes real-world web application development
and deployment more fun, more predictable, and more productive.

.. code-block:: python

   from wsgiref.simple_server import make_server
   from pyramid.config import Configurator
   from pyramid.response import Response

   def hello_world(request):
       return Response('Hello %(name)s!' % request.matchdict)

   if __name__ == '__main__':
       config = Configurator()
       config.add_route('hello', '/hello/{name}')
       config.add_view(hello_world, route_name='hello')
       app = config.make_wsgi_app()
       server = make_server('0.0.0.0', 8080, app)
       server.serve_forever()

Pyramid is a project of the `Pylons Project <http://www.pylonsproject.org/>`_.

Support and Documentation
-------------------------

See `Pyramid Support and Development
<http://docs.pylonsproject.org/projects/pyramid/en/latest/#support-and-development>`_
for documentation, reporting bugs, and getting support.

Developing and Contributing
---------------------------

See `HACKING.txt <https://github.com/Pylons/pyramid/blob/master/HACKING.txt>`_ and
`contributing.md <https://github.com/Pylons/pyramid/blob/master/contributing.md>`_
for guidelines on running tests, adding features, coding style, and updating
documentation when developing in or contributing to Pyramid.

License
-------

Pyramid is offered under the BSD-derived `Repoze Public License
<http://repoze.org/license.html>`_.

Authors
-------

Pyramid is made available by `Agendaless Consulting <https://agendaless.com>`_
and a team of `contributors
<https://github.com/Pylons/pyramid/graphs/contributors>`_.


.. _changes_1.7.3:

1.7.3 (2016-08-17)
==================

Bug Fixes
---------

- Oops, Apparently wheels do not build cleanly every time, so build artifacts
  from 1.6.3 creeped into the wheel for 1.7.2. Note to self: ``rm -rf build``.

.. _changes_1.7.2:

1.7.2 (2016-08-16)
==================

- Revert changes from #2706 released in Pyramid 1.7.1. JSON renderers will
  continue to return unicode data instead of UTF-8 encoded bytes. This means
  that WebOb responses are still expected to handle unicode data even though
  JSON does not have a charset.
  See https://github.com/Pylons/pyramid/issues/2744

.. _changes_1.7.1:

1.7.1 (2016-08-16)
==================

- Change flake8 noqa directive to ignore only a single line instead of the
  entire file in scaffold and documentation. See
  https://github.com/Pylons/pyramid/pull/2646

- Add option to build docs as PDF only via tox. See:
  https://github.com/Pylons/pyramid/issues/2575

- Correct the column type used in the SQLAlchemy + URL Dispatch tutorial by
  changing it from Integer to Text. See
  https://github.com/Pylons/pyramid/pull/2591

- Fix a bug in which the ``password_hash`` in the Wiki2 tutorial was sometimes
  being treated as bytes instead of unicode.
  See https://github.com/Pylons/pyramid/pull/2705

- Properly emit a ``DeprecationWarning`` for using
  ``pyramid.config.Configurator.set_request_property`` instead of
  ``pyramid.config.Configurator.add_request_method``.

- Updated Windows installation instructions and related bits.
  See: https://github.com/Pylons/pyramid/issues/2661

- Fixed bug in `proutes` such that it now shows the correct view when a class
  and `attr` is involved.
  See: https://github.com/Pylons/pyramid/pull/2687

- The JSON renderers now encode their result as UTF-8. The renderer helper
  will now warn the user and encode the result as UTF-8 if a renderer returns a
  text type and the response does not have a valid character set. See
  https://github.com/Pylons/pyramid/pull/2706

1.7 (2016-05-19)
================

- Fix a bug in the wiki2 tutorial where bcrypt is always expecting byte
  strings. See https://github.com/Pylons/pyramid/pull/2576

- Simplify windows detection code and remove some duplicated data.
  See https://github.com/Pylons/pyramid/pull/2585 and
  https://github.com/Pylons/pyramid/pull/2586

1.7b4 (2016-05-12)
==================

- Fixed the exception view tween to re-raise the original exception if
  no exception view could be found to handle the exception. This better
  allows tweens further up the chain to handle exceptions that were
  left unhandled. Previously they would be converted into a
  ``PredicateMismatch`` exception if predicates failed to allow the view to
  handle the exception.
  See https://github.com/Pylons/pyramid/pull/2567

- Exposed the ``pyramid.interfaces.IRequestFactory`` interface to mirror
  the public ``pyramid.interfaces.IResponseFactory`` interface.

1.7b3 (2016-05-10)
==================

- Fix ``request.invoke_exception_view`` to raise an ``HTTPNotFound``
  exception if no view is matched. Previously ``None`` would be returned
  if no views were matched and a ``PredicateMismatch`` would be raised if
  a view "almost" matched (a view was found matching the context).
  See https://github.com/Pylons/pyramid/pull/2564

- Add defaults for py.test configuration and coverage to all three scaffolds,
  and update documentation accordingly.
  See https://github.com/Pylons/pyramid/pull/2550

- Add ``linkcheck`` to ``Makefile`` for Sphinx. To check the documentation for
  broken links, use the command ``make linkcheck
  SPHINXBUILD=$VENV/bin/sphinx-build``. Also removed and fixed dozens of broken
  external links.

- Fix the internal runner for scaffold tests to ensure they work with pip
  and py.test.
  See https://github.com/Pylons/pyramid/pull/2565

1.7b2 (2016-05-01)
==================

- Removed inclusion of pyramid_tm in development.ini for alchemy scaffold
  See https://github.com/Pylons/pyramid/issues/2538

- A default permission set via ``config.set_default_permission`` will no
  longer be enforced on an exception view. This has been the case for a while
  with the default exception views (``config.add_notfound_view`` and
  ``config.add_forbidden_view``), however for any other exception view a
  developer had to remember to set ``permission=NO_PERMISSION_REQUIRED`` or
  be surprised when things didn't work. It is still possible to force a
  permission check on an exception view by setting the ``permission`` argument
  manually to ``config.add_view``. This behavior is consistent with the new
  CSRF features added in the 1.7 series.
  See https://github.com/Pylons/pyramid/pull/2534

1.7b1 (2016-04-25)
==================

- This release announces the beta period for 1.7.

- Fix an issue where some files were being included in the alchemy scafffold
  which had been removed from the 1.7 series.
  See https://github.com/Pylons/pyramid/issues/2525

1.7a2 (2016-04-19)
==================

Features
--------

- Automatic CSRF checks are now disabled by default on exception views. They
  can be turned back on by setting the appropriate `require_csrf` option on
  the view.
  See https://github.com/Pylons/pyramid/pull/2517

- The automatic CSRF API was reworked to use a config directive for
  setting the options. The ``pyramid.require_default_csrf`` setting is
  no longer supported. Instead, a new ``config.set_default_csrf_options``
  directive has been introduced that allows the developer to specify
  the default value for ``require_csrf`` as well as change the CSRF token,
  header and safe request methods. The ``pyramid.csrf_trusted_origins``
  setting is still supported.
  See https://github.com/Pylons/pyramid/pull/2518

Bug fixes
---------

- CSRF origin checks had a bug causing the checks to always fail.
  See https://github.com/Pylons/pyramid/pull/2512

- Fix the test suite to pass on windows.
  See https://github.com/Pylons/pyramid/pull/2520

1.7a1 (2016-04-16)
==================

Backward Incompatibilities
--------------------------

- Following the Pyramid deprecation period (1.4 -> 1.6),
  AuthTktAuthenticationPolicy's default hashing algorithm is changing from md5
  to sha512. If you are using the authentication policy and need to continue
  using md5, please explicitly set hashalg to 'md5'.

  This change does mean that any existing auth tickets (and associated cookies)
  will no longer be valid, and users will no longer be logged in, and have to
  login to their accounts again.

  See https://github.com/Pylons/pyramid/pull/2496

- The ``check_csrf_token`` function no longer validates a csrf token in the
  query string of a request. Only headers and request bodies are supported.
  See https://github.com/Pylons/pyramid/pull/2500

Features
--------

- Added a new setting, ``pyramid.require_default_csrf`` which may be used
  to turn on CSRF checks globally for every POST request in the application.
  This should be considered a good default for websites built on Pyramid.
  It is possible to opt-out of CSRF checks on a per-view basis by setting
  ``require_csrf=False`` on those views.
  See https://github.com/Pylons/pyramid/pull/2413

- Added a ``require_csrf`` view option which will enforce CSRF checks on any
  request with an unsafe method as defined by RFC2616. If the CSRF check fails
  a ``BadCSRFToken`` exception will be raised and may be caught by exception
  views (the default response is a ``400 Bad Request``). This option should be
  used in place of the deprecated ``check_csrf`` view predicate which would
  normally result in unexpected ``404 Not Found`` response to the client
  instead of a catchable exception.  See
  https://github.com/Pylons/pyramid/pull/2413 and
  https://github.com/Pylons/pyramid/pull/2500

- Added an additional CSRF validation that checks the origin/referrer of a
  request and makes sure it matches the current ``request.domain``. This
  particular check is only active when accessing a site over HTTPS as otherwise
  browsers don't always send the required information. If this additional CSRF
  validation fails a ``BadCSRFOrigin`` exception will be raised and may be
  caught by exception views (the default response is ``400 Bad Request``).
  Additional allowed origins may be configured by setting
  ``pyramid.csrf_trusted_origins`` to a list of domain names (with ports if on
  a non standard port) to allow. Subdomains are not allowed unless the domain
  name has been prefixed with a ``.``. See
  https://github.com/Pylons/pyramid/pull/2501

- Added a new ``pyramid.session.check_csrf_origin`` API for validating the
  origin or referrer headers against the request's domain.
  See https://github.com/Pylons/pyramid/pull/2501

- Pyramid HTTPExceptions will now take into account the best match for the
  clients Accept header, and depending on what is requested will return
  text/html, application/json or text/plain. The default for */* is still
  text/html, but if application/json is explicitly mentioned it will now
  receive a valid JSON response. See
  https://github.com/Pylons/pyramid/pull/2489

- A new event and interface (BeforeTraversal) has been introduced that will
  notify listeners before traversal starts in the router. See
  https://github.com/Pylons/pyramid/pull/2469 and
  https://github.com/Pylons/pyramid/pull/1876

- Add a new "view deriver" concept to Pyramid to allow framework authors to
  inject elements into the standard Pyramid view pipeline and affect all
  views in an application. This is similar to a decorator except that it
  has access to options passed to ``config.add_view`` and can affect other
  stages of the pipeline such as the raw response from a view or prior to
  security checks. See https://github.com/Pylons/pyramid/pull/2021

- Allow a leading ``=`` on the key of the request param predicate.
  For example, '=abc=1' is equivalent down to
  ``request.params['=abc'] == '1'``.
  See https://github.com/Pylons/pyramid/pull/1370

- A new ``request.invoke_exception_view(...)`` method which can be used to
  invoke an exception view and get back a response. This is useful for
  rendering an exception view outside of the context of the excview tween
  where you may need more control over the request.
  See https://github.com/Pylons/pyramid/pull/2393

- Allow using variable substitutions like ``%(LOGGING_LOGGER_ROOT_LEVEL)s``
  for logging sections of the .ini file and populate these variables from
  the ``pserve`` command line -- e.g.:
  ``pserve development.ini LOGGING_LOGGER_ROOT_LEVEL=DEBUG``
  See https://github.com/Pylons/pyramid/pull/2399

Documentation Changes
---------------------

- A complete overhaul of the docs:

  - Use pip instead of easy_install.
  - Become opinionated by preferring Python 3.4 or greater to simplify
    installation of Python and its required packaging tools.
  - Use venv for the tool, and virtual environment for the thing created,
    instead of virtualenv.
  - Use py.test and pytest-cov instead of nose and coverage.
  - Further updates to the scaffolds as well as tutorials and their src files.

  See https://github.com/Pylons/pyramid/pull/2468

- A complete overhaul of the ``alchemy`` scaffold as well as the
  Wiki2 SQLAlchemy + URLDispatch tutorial to introduce more modern features
  into the usage of SQLAlchemy with Pyramid and provide a better starting
  point for new projects.
  See https://github.com/Pylons/pyramid/pull/2024

Bug Fixes
---------

- Fix ``pserve --browser`` to use the ``--server-name`` instead of the
  app name when selecting a section to use. This was only working for people
  who had server and app sections with the same name, for example
  ``[app:main]`` and ``[server:main]``.
  See https://github.com/Pylons/pyramid/pull/2292

Deprecations
------------

- The ``check_csrf`` view predicate has been deprecated. Use the
  new ``require_csrf`` option or the ``pyramid.require_default_csrf`` setting
  to ensure that the ``BadCSRFToken`` exception is raised.
  See https://github.com/Pylons/pyramid/pull/2413

- Support for Python 3.3 will be removed in Pyramid 1.8.
  https://github.com/Pylons/pyramid/issues/2477

- Python 2.6 is no longer supported by Pyramid. See
  https://github.com/Pylons/pyramid/issues/2368

- Dropped Python 3.2 support.
  See https://github.com/Pylons/pyramid/pull/2256


