.. _tutorial-github:

How to setup Github authentication?
===================================

In this tutorial, we will authenticate users using Github.

Users obtain a Bearer token from Github and use it in an ``Authenticatìon`` header.
Leveraging Kinto pluggability, a custom authentication policy is specified in settings in order to validate it.

Custom authentication
---------------------

Create a file :file:`kinto_github.py` with the following scaffold:

.. code-block:: python

    from pyramid.authentication import CallbackAuthenticationPolicy
    from pyramid.interfaces import IAuthenticationPolicy
    from zope.interface import implementer

    @implementer(IAuthenticationPolicy)
    class GithubAuthenticationPolicy(CallbackAuthenticationPolicy):
        def __init__(self, realm='Realm'):
            self.realm = realm

        def unauthenticated_userid(self, request):
            user_id = self._get_credentials(request)
            return user_id

        def forget(self, request):
            return [('WWW-Authenticate', 'Bearer realm="%s"' % self.realm)]

        def _get_credentials(self, request):
            authorization = request.headers.get('Authorization', '')
            print('Check Github')


Don't be scared by those lines. It just implements the necessary methods to match the `IAuthenticationPolicy <http://docs.pylonsproject.org/projects/pyramid/en/latest/api/interfaces.html#pyramid.interfaces.IAuthenticationPolicy>`_ Pyramid interface.


Add it to Python path
'''''''''''''''''''''

For the simplicity in this tutorial, we will just alter the ``PYTHONPATH`` system
environment variable. Specify the path to the folder containing the :file:`kinto_github.py`:

::

    $ export PYTHONPATH="/path/to/folder:${PYTHONPATH}"


In order to test that it works, simply try to import it from a ``python`` script:

.. code-block:: shell
    :emphasize-lines: 5

    $ python
    Python 2.7.9 (default, Apr  2 2015, 15:33:21)
    [GCC 4.9.2] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import kinto_github
    >>>


Enable in configuration
'''''''''''''''''''''''

:ref:`As explained in the settings section <configuration-authentication>`, just
enable a new policy pointing to your Python class:

.. code-block:: ini

    multiauth.policies = github basicauth

    multiauth.policy.github.use = kinto_github.GithubAuthenticationPolicy

Kinto should start without errors.


Test it
'''''''

Since we left ``basicauth`` in settings, it should still be accepted:

::

    $ http GET http://localhost:8888/v1/ --auth token:alice-token

.. code-block:: javascript
    :emphasize-lines: 16

    {
        "http_api_version": "1.2",
        "project_docs": "https://kinto.readthedocs.io/",
        "project_name": "kinto",
        "project_version": "1.11.0.dev0",
        "settings": {
            "attachment.base_url": "http://localhost:7777",
            "batch_max_requests": 25,
            "readonly": false
        },
        "url": "http://localhost:8888/v1/",
        "user": {
            "bucket": "71aefbc6-d333-832b-8e39-18da76d11bae",
            "id": "basicauth:63279e82e351f8f318eea09ae5e3bcfc3b9e3eee06e9befacbf17102e0595dad"
        }
    }


And since the ``github`` authentication is also enabled (*but does nothing yet*), you
should see its output in the console when a request comes in.

.. code-block:: shell
    :emphasize-lines: 3

    Starting server in PID 8079.
    serving on http://0.0.0.0:8888
    Check Github
    2016-01-26 11:59:04,918 INFO  [kinto.core.initialization][waitress] "GET   /v1/" 200 (1 ms) request.summary lang=None; uid=63279e82e351f8f318eea09ae5e3bcfc3b9e3eee06e9befacbf17102e0595dad; errno=None; agent=HTTPie/0.9.2; authn_type=BasicAuth; time=2016-01-26T11:59:04


Github token validation
-----------------------

We don't want to make a call to the Github API if the request does not use a Github ``Bearer`` token.

Let's limit this policy to requests with ``github+Bearer`` in ``Authorization`` header.

.. code-block:: python
    :emphasize-lines: 21-27

    from pyramid.authentication import CallbackAuthenticationPolicy
    from pyramid.interfaces import IAuthenticationPolicy
    from zope.interface import implementer

    GITHUB_METHOD = 'github+bearer'

    @implementer(IAuthenticationPolicy)
    class GithubAuthenticationPolicy(CallbackAuthenticationPolicy):
        def __init__(self, realm='Realm'):
            self.realm = realm

        def unauthenticated_userid(self, request):
            user_id = self._get_credentials(request)
            return user_id

        def forget(self, request):
            return [('WWW-Authenticate', '%s realm="%s"' % (GITHUB_METHOD, self.realm)]

        def _get_credentials(self, request):
            authorization = request.headers.get('Authorization', '')
            try:
                authmeth, token = authorization.split(' ', 1)
                authmeth = authmeth.lower()
            except ValueError:
                return None
            if authmeth != GITHUB_METHOD.lower():
                return None
            print('Check Github')


Now using Basic Authentication it should be skipped, but with this request it should print it in the server console:

::

    $ http http://localhost:8888/v1/ "Authorization: github+Bearer foobartoken"


Validate token while obtaining user id from Github
''''''''''''''''''''''''''''''''''''''''''''''''''

We will simply make a call to the Github user API and try to obtain the ``login`` attribute (i.e. user name).

.. code-block:: python
    :emphasize-lines: 30-38

    import requests
    from kinto.core import logger
    from pyramid.authentication import CallbackAuthenticationPolicy
    from pyramid.interfaces import IAuthenticationPolicy
    from zope.interface import implementer

    GITHUB_METHOD = 'Github+Bearer'

    @implementer(IAuthenticationPolicy)
    class GithubAuthenticationPolicy(CallbackAuthenticationPolicy):
        def __init__(self, realm='Realm'):
            self.realm = realm

        def unauthenticated_userid(self, request):
            user_id = self._get_credentials(request)
            return user_id

        def forget(self, request):
            return [('WWW-Authenticate', '%s realm="%s"' % (GITHUB_METHOD, self.realm)]

        def _get_credentials(self, request):
            authorization = request.headers.get('Authorization', '')
            try:
                authmeth, token = authorization.split(' ', 1)
                authmeth = authmeth.lower()
            except ValueError:
                return None
            if authmeth != GITHUB_METHOD.lower():
                return None
            try:
                headers = {"Authorization": "token %s" % token}
                resp = requests.get("https://api.github.com/user", headers=headers)
                resp.raise_for_status()
                userinfo = resp.json()
                user_id = userinfo['login']
            except Exception as e:
                logger.warn(e)
                return None


Let's try to create an object on Kinto, it should fail using a ``401 Unauthorized`` error response using a dummy token:

::

    $ http PUT http://localhost:8888/v1/buckets/test "Authorization: github+Bearer foobartoken"

.. code-block:: http

    HTTP/1.1 401 Unauthorized
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 110
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 26 Jan 2016 11:07:05 GMT
    Server: waitress
    Www-Authenticate: Github+Bearer realm="Realm"
    Www-Authenticate: Basic realm="Realm"

    {
        "code": 401,
        "errno": 104,
        "error": "Unauthorized",
        "message": "Please authenticate yourself to use this endpoint."
    }


Test it!
--------

Obtain a Personal Access token
''''''''''''''''''''''''''''''

Create a *Personal access token* using the Github API using your user/pass:

.. code-block:: shell

    $ echo '{"note": "Kinto Github tutorial"}' | http POST https://api.github.com/authorizations --auth token:user-token

It is returned in the ``token`` attribute in the JSON response:

.. code-block:: http
    :emphasize-lines: 19

    HTTP/1.1 201 Created
    Access-Control-Allow-Credentials: true
    Access-Control-Allow-Origin: *

    {
        "app": {
            "client_id": "00000000000000000000",
            "name": "Kinto Github tutorial",
            "url": "https://developer.github.com/v3/oauth_authorizations/"
        },
        "created_at": "2016-01-26T11:09:02Z",
        "fingerprint": null,
        "hashed_token": "15eb9f...e8aa4502",
        "id": 27212889,
        "note": "kinto",
        "note_url": null,
        "scopes": [],
        "token": "7f7f911969279d8b16a12f44b8bc6e2d216dc51e",
        "token_last_eight": "c30211c6",
        "updated_at": "2016-01-26T11:09:02Z",
        "url": "https://api.github.com/authorizations/27212889"
    }

.. note::

    If you have two-factor auth enabled, please refer to the `Github API documentation <https://developer.github.com/v3/oauth/>`_
    for obtaining a Personal access token using the appropriate headers.


Check your user id
''''''''''''''''''

.. code-block:: shell

    $ http http://localhost:8888/v1/ "Authorization: github+Bearer 7f7f911969279d8b16a12f44b8bc6e2d216dc51e"

.. code-block:: http
    :emphasize-lines: 23

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 406
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 26 Jan 2016 11:05:09 GMT
    Server: waitress

    {
        "http_api_version": "1.2",
        "project_docs": "https://kinto.readthedocs.io/",
        "project_name": "kinto",
        "project_version": "1.11.0.dev0",
        "settings": {
            "attachment.base_url": "http://localhost:7777",
            "batch_max_requests": 25,
            "readonly": false
        },
        "url": "http://localhost:8888/v1/",
        "user": {
            "bucket": "8f730aef-55cb-f1d0-4b0e-c8afbe767c63",
            "id": "github:leplatrem"
        }
    }


Use it in permissions
'''''''''''''''''''''

The user id ``github:<username>`` can now be used in permissions definitions.
It is much more convenient than Basic Auth identifiers!

::

    $ echo '{"permissions": {"read": ["github:leplatrem"]}}' | \
        http PUT http://localhost:8888/v0/buckets/test  --auth='token:another-user-token'


Cache the token validation
''''''''''''''''''''''''''

Using the following snippet you can cache the association between a token and the user id, in order to avoid requesting Github at each request.

It uses Kinto internal cache backend (*if configured*):

.. code-block:: python

    if not hasattr(request.registry, 'cache'):
        return fetch_github(token)

    cache = request.registry.cache
    cache_key = "token_github:" + token
    user_id = cache.get(cache_key)
    if not user_id:
        user_id = fetch_github(token)
        cache.set(cache_key, user_id, ttl=3600*24)  # cache during 24H


Next steps
----------

Now that this policy works as expected, you can bring it to the next level!

For example:

* Contribute it as built-in policy in Kinto! (*We need you!*)
* Contribute another policy based on another method (e.g. Twitter, JSON Web token etc.)
* Build a Webpage and try obtaining a token in a Web flow (`see Github docs <https://developer.github.com/v3/oauth/>`_)
* Allow passing the Github token in the querystring in addition to ``Authorization`` header (*for convience*)

Don't hesitate to contact us!
