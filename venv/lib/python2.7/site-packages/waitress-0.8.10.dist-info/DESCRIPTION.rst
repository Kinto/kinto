Waitress is meant to be a production-quality pure-Python WSGI server with very
acceptable performance.  It has no dependencies except ones which live in the
Python standard library.  It runs on CPython on Unix and Windows under Python
2.6+ and Python 3.2+.  It is also known to run on PyPy 1.6.0+ on UNIX.  It
supports HTTP/1.0 and HTTP/1.1.

For more information, see the "docs" directory of the Waitress package or
http://docs.pylonsproject.org/projects/waitress/en/latest/ .


0.8.10 (2015-08-02)
-------------------

- Add support for Python 3.4, 3.5b2, and PyPy3.

- Use a nonglobal asyncore socket map by default, trying to prevent conflicts
  with apps and libs that use the asyncore global socket map ala
  https://github.com/Pylons/waitress/issues/63.  You can get the old
  use-global-socket-map behavior back by passing ``asyncore.socket_map`` to the
  ``create_server`` function as the ``map`` argument.

- Waitress violated PEP 3333 with respect to reraising an exception when
  ``start_response`` was called with an ``exc_info`` argument.  It would
  reraise the exception even if no data had been sent to the client.  It now
  only reraises the exception if data has actually been sent to the client.
  See https://github.com/Pylons/waitress/pull/52 and
  https://github.com/Pylons/waitress/issues/51

- Add a ``docs`` section to tox.ini that, when run, ensures docs can be built.

- If an ``application`` value of ``None`` is supplied to the ``create_server``
  constructor function, a ValueError is now raised eagerly instead of an error
  occuring during runtime.  See https://github.com/Pylons/waitress/pull/60

- Fix parsing of multi-line (folded) headers.
  See https://github.com/Pylons/waitress/issues/53 and
  https://github.com/Pylons/waitress/pull/90

- Switch from the low level Python thread/_thread module to the threading
  module.

- Improved exception information should module import go awry.

0.8.9 (2014-05-16)
------------------

- Fix tests under Windows.  NB: to run tests under Windows, you cannot run
  "setup.py test" or "setup.py nosetests".  Instead you must run ``python.exe
  -c "import nose; nose.main()"``.  If you try to run the tests using the
  normal method under Windows, each subprocess created by the test suite will
  attempt to run the test suite again.  See
  https://github.com/nose-devs/nose/issues/407 for more information.

- Give the WSGI app_iter generated when ``wsgi.file_wrapper`` is used
  (ReadOnlyFileBasedBuffer) a ``close`` method.  Do not call ``close`` on an
  instance of such a class when it's used as a WSGI app_iter, however.  This is
  part of a fix which prevents a leakage of file descriptors; the other part of
  the fix was in WebOb
  (https://github.com/Pylons/webob/commit/951a41ce57bd853947f842028bccb500bd5237da).

- Allow trusted proxies to override ``wsgi.url_scheme`` via a request header,
  ``X_FORWARDED_PROTO``.  Allows proxies which serve mixed HTTP / HTTPS
  requests to control signal which are served as HTTPS.  See
  https://github.com/Pylons/waitress/pull/42.

0.8.8 (2013-11-30)
------------------

- Fix some cases where the creation of extremely large output buffers (greater
  than 2GB, suspected to be buffers added via ``wsgi.file_wrapper``) might
  cause an OverflowError on Python 2.  See
  https://github.com/Pylons/waitress/issues/47.

- When the ``url_prefix`` adjustment starts with more than one slash, all
  slashes except one will be stripped from its beginning.  This differs from
  older behavior where more than one leading slash would be preserved in
  ``url_prefix``.

- If a client somehow manages to send an empty path, we no longer convert the
  empty path to a single slash in ``PATH_INFO``.  Instead, the path remains
  empty.  According to RFC 2616 section "5.1.2 Request-URI", the scenario of a
  client sending an empty path is actually not possible because the request URI
  portion cannot be empty.

- If the ``url_prefix`` adjustment matches the request path exactly, we now
  compute ``SCRIPT_NAME`` and ``PATH_INFO`` properly.  Previously, if the
  ``url_prefix`` was ``/foo`` and the path received from a client was ``/foo``,
  we would set *both* ``SCRIPT_NAME`` and ``PATH_INFO`` to ``/foo``.  This was
  incorrect.  Now in such a case we set ``PATH_INFO`` to the empty string and
  we set ``SCRIPT_NAME`` to ``/foo``.  Note that the change we made has no
  effect on paths that do not match the ``url_prefix`` exactly (such as
  ``/foo/bar``); these continue to operate as they did.  See
  https://github.com/Pylons/waitress/issues/46

- Preserve header ordering of headers with the same name as per RFC 2616.  See
  https://github.com/Pylons/waitress/pull/44

- When waitress receives a ``Transfer-Encoding: chunked`` request, we no longer
  send the ``TRANSFER_ENCODING`` nor the ``HTTP_TRANSFER_ENCODING`` value to
  the application in the environment.  Instead, we pop this header.  Since we
  cope with chunked requests by buffering the data in the server, we also know
  when a chunked request has ended, and therefore we know the content length.
  We set the content-length header in the environment, such that applications
  effectively never know the original request was a T-E: chunked request; it
  will appear to them as if the request is a non-chunked request with an
  accurate content-length.

- Cope with the fact that the ``Transfer-Encoding`` value is case-insensitive.

- When the ``--unix-socket-perms`` option was used as an argument to
  ``waitress-serve``, a ``TypeError`` would be raised.  See
  https://github.com/Pylons/waitress/issues/50.

0.8.7 (2013-08-29)
------------------

- The HTTP version of the response returned by waitress when it catches an
  exception will now match the HTTP request version.

- Fix: CONNECTION header will be HTTP_CONNECTION and not CONNECTION_TYPE
  (see https://github.com/Pylons/waitress/issues/13)

0.8.6 (2013-08-12)
------------------

- Do alternate type of checking for UNIX socket support, instead of checking
  for platform == windows.

- Functional tests now use multiprocessing module instead of subprocess module,
  speeding up test suite and making concurrent execution more reliable.

- Runner now appends the current working directory to ``sys.path`` to support
  running WSGI applications from a directory (i.e., not installed in a
  virtualenv).

- Add a ``url_prefix`` adjustment setting.  You can use it by passing
  ``script_name='/foo'`` to ``waitress.serve`` or you can use it in a
  ``PasteDeploy`` ini file as ``script_name = /foo``.  This will cause the WSGI
  ``SCRIPT_NAME`` value to be the value passed minus any trailing slashes you
  add, and it will cause the ``PATH_INFO`` of any request which is prefixed
  with this value to be stripped of the prefix.  You can use this instead of
  PasteDeploy's ``prefixmiddleware`` to always prefix the path.

0.8.5 (2013-05-27)
------------------

- Fix runner multisegment imports in some Python 2 revisions (see
  https://github.com/Pylons/waitress/pull/34).

- For compatibility, WSGIServer is now an alias of TcpWSGIServer. The
  signature of BaseWSGIServer is now compatible with WSGIServer pre-0.8.4.

0.8.4 (2013-05-24)
------------------

- Add a command-line runner called ``waitress-serve`` to allow Waitress
  to run WSGI applications without any addional machinery. This is
  essentially a thin wrapper around the ``waitress.serve()`` function.

- Allow parallel testing (e.g., under ``detox`` or ``nosetests --processes``)
  using PID-dependent port / socket for functest servers.

- Fix integer overflow errors on large buffers. Thanks to Marcin Kuzminski
  for the patch.  See: https://github.com/Pylons/waitress/issues/22

- Add support for listening on Unix domain sockets.

0.8.3 (2013-04-28)
------------------

Features
~~~~~~~~

- Add an ``asyncore_loop_timeout`` adjustment value, which controls the
  ``timeout`` value passed to ``asyncore.loop``; defaults to 1.

Bug Fixes
~~~~~~~~~

- The default asyncore loop timeout is now 1 second.  This prevents slow
  shutdown on Windows.  See https://github.com/Pylons/waitress/issues/6 .  This
  shouldn't matter to anyone in particular, but it can be changed via the
  ``asyncore_loop_timeout`` adjustment (it used to previously default to 30
  seconds).

- Don't complain if there's a response to a HEAD request that contains a
  Content-Length > 0.  See https://github.com/Pylons/waitress/pull/7.

- Fix bug in HTTP Expect/Continue support.  See
  https://github.com/Pylons/waitress/issues/9 .


0.8.2 (2012-11-14)
------------------

Bug Fixes
~~~~~~~~~

- http://corte.si/posts/code/pathod/pythonservers/index.html pointed out that
  sending a bad header resulted in an exception leading to a 500 response
  instead of the more proper 400 response without an exception.

- Fix a race condition in the test suite.

- Allow "ident" to be used as a keyword to ``serve()`` as per docs.

- Add py33 to tox.ini.

0.8.1 (2012-02-13)
------------------

Bug Fixes
~~~~~~~~~

- A brown-bag bug prevented request concurrency.  A slow request would block
  subsequent the responses of subsequent requests until the slow request's
  response was fully generated.  This was due to a "task lock" being declared
  as a class attribute rather than as an instance attribute on HTTPChannel.
  Also took the opportunity to move another lock named "outbuf lock" to the
  channel instance rather than the class.  See
  https://github.com/Pylons/waitress/pull/1 .

0.8 (2012-01-31)
----------------

Features
~~~~~~~~

- Support the WSGI ``wsgi.file_wrapper`` protocol as per
  http://www.python.org/dev/peps/pep-0333/#optional-platform-specific-file-handling.
  Here's a usage example::

    import os

    here = os.path.dirname(os.path.abspath(__file__))

    def myapp(environ, start_response):
        f = open(os.path.join(here, 'myphoto.jpg'), 'rb')
        headers = [('Content-Type', 'image/jpeg')]
        start_response(
            '200 OK',
            headers
            )
        return environ['wsgi.file_wrapper'](f, 32768)

  The signature of the file wrapper constructor is ``(filelike_object,
  block_size)``.  Both arguments must be passed as positional (not keyword)
  arguments.  The result of creating a file wrapper should be **returned** as
  the ``app_iter`` from a WSGI application.

  The object passed as ``filelike_object`` to the wrapper must be a file-like
  object which supports *at least* the ``read()`` method, and the ``read()``
  method must support an optional size hint argument.  It *should* support
  the ``seek()`` and ``tell()`` methods.  If it does not, normal iteration
  over the filelike object using the provided block_size is used (and copying
  is done, negating any benefit of the file wrapper).  It *should* support a
  ``close()`` method.

  The specified ``block_size`` argument to the file wrapper constructor will
  be used only when the ``filelike_object`` doesn't support ``seek`` and/or
  ``tell`` methods.  Waitress needs to use normal iteration to serve the file
  in this degenerate case (as per the WSGI spec), and this block size will be
  used as the iteration chunk size.  The ``block_size`` argument is optional;
  if it is not passed, a default value``32768`` is used.

  Waitress will set a ``Content-Length`` header on the behalf of an
  application when a file wrapper with a sufficiently filelike object is used
  if the application hasn't already set one.

  The machinery which handles a file wrapper currently doesn't do anything
  particularly special using fancy system calls (it doesn't use ``sendfile``
  for example); using it currently just prevents the system from needing to
  copy data to a temporary buffer in order to send it to the client.  No
  copying of data is done when a WSGI app returns a file wrapper that wraps a
  sufficiently filelike object.  It may do something fancier in the future.

0.7 (2012-01-11)
----------------

Features
~~~~~~~~

- Default ``send_bytes`` value is now 18000 instead of 9000.  The larger
  default value prevents asyncore from needing to execute select so many
  times to serve large files, speeding up file serving by about 15%-20% or
  so.  This is probably only an optimization for LAN communications, and
  could slow things down across a WAN (due to higher TCP overhead), but we're
  likely to be behind a reverse proxy on a LAN anyway if in production.

- Added an (undocumented) profiling feature to the ``serve()`` command.

0.6.1 (2012-01-08)
------------------

Bug Fixes
~~~~~~~~~

- Remove performance-sapping call to ``pull_trigger`` in the channel's
  ``write_soon`` method added mistakenly in 0.6.

0.6 (2012-01-07)
----------------

Bug Fixes
~~~~~~~~~

- A logic error prevented the internal outbuf buffer of a channel from being
  flushed when the client could not accept the entire contents of the output
  buffer in a single succession of socket.send calls when the channel was in
  a "pending close" state.  The socket in such a case would be closed
  prematurely, sometimes resulting in partially delivered content.  This was
  discovered by a user using waitress behind an Nginx reverse proxy, which
  apparently is not always ready to receive data.  The symptom was that he
  received "half" of a large CSS file (110K) while serving content via
  waitress behind the proxy.

0.5 (2012-01-03)
----------------

Bug Fixes
~~~~~~~~~

- Fix PATH_INFO encoding/decoding on Python 3 (as per PEP 3333, tunnel
  bytes-in-unicode-as-latin-1-after-unquoting).

0.4 (2012-01-02)
----------------

Features
~~~~~~~~

- Added "design" document to docs.

Bug Fixes
~~~~~~~~~

- Set default ``connection_limit`` back to 100 for benefit of maximal
  platform compatibility.

- Normalize setting of ``last_activity`` during send.

- Minor resource cleanups during tests.

- Channel timeout cleanup was broken.

0.3 (2012-01-02)
----------------

Features
~~~~~~~~

- Dont hang a thread up trying to send data to slow clients.

- Use self.logger to log socket errors instead of self.log_info (normalize).

- Remove pointless handle_error method from channel.

- Queue requests instead of tasks in a channel.

Bug Fixes
~~~~~~~~~

- Expect: 100-continue responses were broken.


0.2 (2011-12-31)
----------------

Bug Fixes
~~~~~~~~~

- Set up logging by calling logging.basicConfig() when ``serve`` is called
  (show tracebacks and other warnings to console by default).

- Disallow WSGI applications to set "hop-by-hop" headers (Connection,
  Transfer-Encoding, etc).

- Don't treat 304 status responses specially in HTTP/1.1 mode.

- Remove out of date ``interfaces.py`` file.

- Normalize logging (all output is now sent to the ``waitress`` logger rather
  than in degenerate cases some output being sent directly to stderr).

Features
~~~~~~~~

- Support HTTP/1.1 ``Transfer-Encoding: chunked`` responses.

- Slightly better docs about logging.

0.1 (2011-12-30)
----------------

- Initial release.


