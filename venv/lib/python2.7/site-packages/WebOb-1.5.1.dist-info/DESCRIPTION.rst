WebOb
=====

.. image:: https://travis-ci.org/Pylons/webob.png?branch=master
        :target: https://travis-ci.org/Pylons/webob

.. image:: https://readthedocs.org/projects/webob/badge/?version=latest
        :target: http://docs.pylonsproject.org/projects/webob/en/latest/
        :alt: Documentation Status

WebOb provides objects for HTTP requests and responses.  Specifically
it does this by wrapping the `WSGI <http://wsgi.org>`_ request
environment and response status/headers/app_iter(body).

The request and response objects provide many conveniences for parsing
HTTP request and forming HTTP responses.  Both objects are read/write:
as a result, WebOb is also a nice way to create HTTP requests and
parse HTTP responses.

Support and Documentation
-------------------------

See the `WebOb Documentation website <http://webob.readthedocs.org/>`_ to view
documentation, report bugs, and obtain support.

License
-------

WebOb is offered under the `MIT-license
<http://webob.readthedocs.org/en/latest/license.html>`_.

Authors
-------

WebOb was authored by Ian Bicking and is currently maintained by the `Pylons
Project <http://pylonsproject.org/>`_ and a team of contributors.



1.5.1 (2015-10-30)
------------------

Bug Fixes
~~~~~~~~~

- The exceptions HTTPNotAcceptable, HTTPUnsupportedMediaType and
  HTTPNotImplemented will now correctly use the sub-classed template rather
  than the default error template. See https://github.com/Pylons/webob/issues/221

- Response's from_file now correctly deals with a status line that contains an
  HTTP version identifier. HTTP/1.1 200 OK is now correctly parsed, whereas
  before this would raise an error upon setting the Response.status in
  from_file. See https://github.com/Pylons/webob/issues/121

1.5.0 (2015-10-11)
------------------

Bug Fixes
~~~~~~~~~

- The cookie API functions will now make sure that `max_age` is an integer or
  an string that can convert to an integer. Previously passing in
  max_age='test' would have silently done the wrong thing.

1.5.0b0 (2015-09-06)
--------------------

Bug Fixes
~~~~~~~~~

- Unbreak req.POST when the request method is PATCH. Instead of returning
  something cmpletely unrelated we return NoVar. See:
  https://github.com/Pylons/webob/pull/215

Features
~~~~~~~~

- HTTP Status Code 308 is now supported as a Permanent Redirect. See
  https://github.com/Pylons/webob/pull/207

1.5.0a1 (2015-07-30)
--------------------

Backwards Incompatibilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``Response.set_cookie`` renamed the only required parameter from "key" to
  "name". The code will now still accept "key" as a keyword argument, and will
  issue a DeprecationWarning until WebOb 1.7.

- The ``status`` attribute of a ``Response`` object no longer takes a string
  like ``None None`` and allows that to be set as the status. It now has to at
  least match the pattern of ``<integer status code> <explenation of status
  code>``. Invalid status strings will now raise a ``ValueError``.

1.5.0a0 (2015-07-25)
--------------------

Backwards Incompatibilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``Morsel`` will no longer accept a cookie value that does not meet RFC6265's
  cookie-octet specification. Upon calling ``Morsel.serialize`` a warning will
  be issued, in the future this will raise a ``ValueError``, please update your
  cookie handling code. See https://github.com/Pylons/webob/pull/172

  The cookie-octet specification in RFC6265 states the following characters are
  valid in a cookie value:

  ===============  =======================================
  Hex Range        Actual Characters
  ===============  =======================================
  ``[0x21     ]``  ``!``
  ``[0x25-0x2B]``  ``#$%&'()*+``
  ``[0x2D-0x3A]``  ``-./0123456789:``
  ``[0x3C-0x5B]``  ``<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[``
  ``[0x5D-0x7E]``  ``]^_`abcdefghijklmnopqrstuvwxyz{|}~``
  ===============  =======================================

  RFC6265 suggests using base 64 to serialize data before storing data in a
  cookie.

  Cookies that meet the RFC6265 standard will no longer be quoted, as this is
  unnecessary. This is a no-op as far as browsers and cookie storage is
  concerned.

- ``Response.set_cookie`` now uses the internal ``make_cookie`` API, which will
  issue warnings if cookies are set with invalid bytes. See
  https://github.com/Pylons/webob/pull/172

Features
~~~~~~~~

- Add support for some new caching headers, stale-while-revalidate and
  stale-if-error that can be used by reverse proxies to cache stale responses
  temporarily if the backend disappears. From RFC5861. See
  https://github.com/Pylons/webob/pull/189

Bug Fixes
~~~~~~~~~

- Response.status now uses duck-typing for integers, and has also learned to
  raise a ValueError if the status isn't an integer followed by a space, and
  then the reason. See https://github.com/Pylons/webob/pull/191

- Fixed a bug in ``webob.multidict.GetDict`` which resulted in the
  QUERY_STRING not being updated when changes were made to query
  params using ``Request.GET.extend()``.

- Read the body of a request if we think it might have a body. This fixes PATCH
  to support bodies. See https://github.com/Pylons/webob/pull/184

- Response.from_file returns HTTP headers as latin1 rather than UTF-8, this
  fixes the usage on Google AppEngine. See
  https://github.com/Pylons/webob/issues/99 and
  https://github.com/Pylons/webob/pull/150

- Fix a bug in parsing the auth parameters that contained bad white space. This
  makes the parsing fall in line with what's required in RFC7235. See
  https://github.com/Pylons/webob/issues/158

- Use '\r\n' line endings in ``Response.__str__``. See:
  https://github.com/Pylons/webob/pull/146

Documentation Changes
~~~~~~~~~~~~~~~~~~~~~

- ``response.set_cookie`` now has proper documentation for ``max_age`` and
  ``expires``. The code has also been refactored to use ``cookies.make_cookie``
  instead of duplicating the code. This fixes
  https://github.com/Pylons/webob/issues/166 and
  https://github.com/Pylons/webob/issues/171

- Documentation didn't match the actual code for the wsgify function signature.
  See https://github.com/Pylons/webob/pull/167

- Remove the WebDAV only from certain HTTP Exceptions, these exceptions may
  also be used by REST services for example.


