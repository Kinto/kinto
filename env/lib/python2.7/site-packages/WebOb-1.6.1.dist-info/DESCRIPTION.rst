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



1.6.1 (2016-05-20)
------------------

Bugfix
~~~~~~

- Response.from_file now parses the status line correctly when the status line
  contains an HTTP with version, as well as a status text that contains
  multiple white spaces (e.g 404 Not Found). See
  https://github.com/Pylons/webob/issues/250


1.6.0 (2016-03-15)
------------------

Compatibility
~~~~~~~~~~~~~

- Python 3.2 is no longer supported by WebOb

Bugfix
~~~~~~

- Request.decode attempted to read from the an already consumed stream, it has
  now been redirected to another stream to read from. See
  https://github.com/Pylons/webob/pull/183

- The application/json media type does not allow for a charset as discovery of
  the encoding is done at the JSON layer. Upon initialization of a Response
  WebOb will no longer add a charset if the content-type is set to JSON. See
  https://github.com/Pylons/webob/pull/197 and
  https://github.com/Pylons/pyramid/issues/1611

Features
~~~~~~~~

- Lazily HTML escapes environment keys in HTTP Exceptions so that those keys in
  the environ that are not used in the output of the page don't raise an
  exception due to inability to be properly escaped. See
  https://github.com/Pylons/webob/pull/139

- MIMEAccept now accepts comparisons against wildcards, this allows one to
  match on just the media type or sub-type, without having to explicitly match
  on both the media type and sub-type at the same time. See
  https://github.com/Pylons/webob/pull/185

- Add the ability to return a JSON body from an exception. Using the Accept
  information in the request, the exceptions will now automatically return a
  JSON version of the exception instead of just HTML or text. See
  https://github.com/Pylons/webob/pull/230 and
  https://github.com/Pylons/webob/issues/209

Security
~~~~~~~~

- exc._HTTPMove and any subclasses will now raise a ValueError if the location
  field contains a line feed or carriage return. These values may lead to
  possible HTTP Response Splitting. The header_getter descriptor has also been
  modified to no longer accept headers with a line feed or carriage return.
  See: https://github.com/Pylons/webob/pull/229 and
  https://github.com/Pylons/webob/issues/217



