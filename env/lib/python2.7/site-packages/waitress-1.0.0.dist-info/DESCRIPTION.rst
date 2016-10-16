Waitress is meant to be a production-quality pure-Python WSGI server with very
acceptable performance.  It has no dependencies except ones which live in the
Python standard library.  It runs on CPython on Unix and Windows under Python
2.7+ and Python 3.3+.  It is also known to run on PyPy 1.6.0+ on UNIX.  It
supports HTTP/1.0 and HTTP/1.1.

For more information, see the "docs" directory of the Waitress package or
http://docs.pylonsproject.org/projects/waitress/en/latest/ .


1.0.0 (2016-08-31)
------------------

Bugfixes
~~~~~~~~

- Removed `AI_ADDRCONFIG` from the call to `getaddrinfo`, this resolves an
  issue whereby `getaddrinfo` wouldn't return any addresses to `bind` to on
  hosts where there is no internet connection but localhost is requested to be
  bound to. See https://github.com/Pylons/waitress/issues/131 for more
  information.

Deprecations
~~~~~~~~~~~~

- Python 2.6 is no longer supported.

Features
~~~~~~~~

- IPv6 support

- Waitress is now able to listen on multiple sockets, including IPv4 and IPv6.
  Instead of passing in a host/port combination you now provide waitress with a
  space delineated list, and it will create as many sockets as required.

  .. code-block:: python

	from waitress import serve
	serve(wsgiapp, listen='0.0.0.0:8080 [::]:9090 *:6543')

Security
~~~~~~~~

- Waitress will now drop HTTP headers that contain an underscore in the key
  when received from a client. This is to stop any possible underscore/dash
  conflation that may lead to security issues. See
  https://github.com/Pylons/waitress/pull/80 and
  https://www.djangoproject.com/weblog/2015/jan/13/security/


