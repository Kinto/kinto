##############
Authentication
##############

.. _authentication:

A word about users
==================

First of all, Kinto **doesn't provide users management**. There is no such thing
as user sign-up, password modification, etc.

However, since Kinto handles permissions on objects, users are uniquely
identified.

How is that possible?
---------------------

Kinto uses the request headers to authenticate the current user.

Depending on the authentication methods enabled in configuration,
the HTTP method to authenticate requests may differ.

Kinto can rely on a third-party called «`Identity provider <https://en.wikipedia.org/wiki/Identity_provider>`_»
to authenticate the request and assign a :term:`user id`.

There are many identity providers solutions in the wild. The most common are OAuth,
JWT, SAML, x509, Hawk sessions...

A policy based on *OAuth2 bearer tokens* is recommended, but not mandatory.

Low tech included
-----------------

Kinto has no third-party policy included (yet!), and only provides a policy based on
Basic Authentication.

Depending on your use case, you may want to plug GitHub, Facebook, Google, or your
company identity provider. It is rather easy, :ref:`follow our tutorial <tutorial-github>`!

.. note::

    If you believe that Kinto must provide some third parties providers by default,
    please come reach us!

    There are many tools in the Python/Pyramid ecosystem, it is probably just
    a matter of documenting their setup.


Multiple policies
-----------------

It is possible to enable several authentication methods.
See :ref:`configuration <configuration-authentication>`.

In the current implementation, when multiple policies are configured,
the first one in the list that succeeds is picked.

:term:`User identifiers` are prefixed with the policy name being used.


Basic Auth
==========

In most examples in this documentation we use the built-in Basic Authentication,
which computes a user id based on the token provided in the request.

.. warning::

    This method has many limitations but has the advantage of not needing
    specific setup or third-party services before you get started.

When using arbitrary tokens make sure that:

 - each user has a different one;
 - a user always uses the same token.

You can check if Basic Auth is enabled on the server side by checking
the ``basicauth`` capability.


How to Authenticate with Basic Auth?
------------------------------------

Depending on configuration (*enabled by default*), using a *Basic Auth* token
will associate a unique :term:`user identifier` to any username/password combination.

::

    Authorization: Basic <basic_token>

The token shall be built using this formula ``base64("token:<secret>")``.

Since any string is accepted, here we use ``token`` only by convention.
Empty secrets are accepted and can be anything (custom, UUID, etc.)

If the header has an invalid format, or if *Basic Auth* is not enabled,
this will result in a |status-401| error response.

.. warning::

    Since :term:`user id` is derived from the token, there is no way
    to change the token without "losing" permissions on existing records.
    See below for more information.


How does Kinto know it is a valid Basic Auth token?
---------------------------------------------------

For each token, Kinto will calculate a unique user ID which is
related to your Kinto instance. It uses a bit of cryptography and the value of
the ``user_hmac_secret`` setting.

In other words, every string provided in the *Basic Auth* header will be valid,
and will lead to a unique user ID.

.. note::

    Two Kinto instances using the same ``user_hmac_secret`` will
    generate the same user ID for a given Basic Auth token.

You can obtain the :term:`user ID` generated for your token on the :ref:`Kinto root URL <api-utilities>`:

.. code-block:: shell

    $ http https://kinto.dev.mozaws.net/v1/ --auth "token:my-secret"

.. code-block:: http
    :emphasize-lines: 24

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Connection: keep-alive
    Content-Length: 498
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 29 Jan 2016 09:13:33 GMT
    Server: nginx

    {
        "http_api_version": "1.0",
        "project_docs": "https://kinto.readthedocs.io/",
        "project_name": "kinto",
        "project_version": "1.10.0",
        "settings": {
            "attachment.base_url": "https://kinto.dev.mozaws.net/attachments/",
            "batch_max_requests": 25,
            "readonly": false
        },
        "url": "https://kinto.dev.mozaws.net/v1/",
        "user": {
            "bucket": "e777874f-2936-11a1-3269-68a6c1648a92",
            "id": "basicauth:c635be9375673027e9b2f357a3955a0a46b58aeface61930838b61e946008ab0"
        }
    }

As soon as this user ID is used to give permission on an object
(buckets, groups, collections, records), the user will be granted that
permission when using this token.


How can we generate strong unique tokens?
-----------------------------------------

For certain use cases, tokens can be public and shared publicly. For others, they must
be kept secret.

For the latter, we recommend using at least a 16 random bytes strings, such as UUIDs:

Using the ``uuidgen`` CLI tool:

.. code-block:: shell

    $ uuidgen
    3a96294b-4e75-4e32-958d-fea44f2fe5aa

Using Python:

.. code-block:: pycon

    >>> from uuid import uuid4
    >>> print(uuid4())
    6f8dfa43-668c-4e5c-89bc-eaabcb866342

Using Node:

.. code-block:: js

    > var uuid = require('node-uuid');
    > console.log(uuid.v4());
    0a859a0e-4e6e-4014-896a-aa85d9587c48

Then the string obtained can be used as it is:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/ \
        --auth "token:6f8dfa43-668c-4e5c-89bc-eaabcb866342"

And observe the user ID in the response.


How can I change the token for a given user?
--------------------------------------------

Asking yourself this question is a first sign that you should not be
using the Basic Auth authentication method for your use case.

Because the user ID is computed from the token, changing the token
will change the user ID.

Some possible strategies:

- You can generate new tokens and give the ``write`` permission to their
  respective user id.

- You can also create a group per « user » whose members are the different
  user IDs obtained from tokens. And then use this group in permission
  definitions on objects.

- Most likely, you would use an identity provider which will be in
  charge of user and token management (generate, refresh, validate, ...).
  `See this example with Django <https://django-oauth-toolkit.readthedocs.io/en/latest/tutorial/tutorial_01.html>`_.

You can also read our :ref:`tutorial about how to plug the GitHub authorisation backend <tutorial-github>`.


.. _authentication-openid:

OpenID Connect
==============

OpenID relies on *OAuth2 bearer tokens*, so basically authentication shall be done using this header:

::

    Authorization: Bearer <access_token>

:notes:

    If the token is not valid, this will result in a |status-401| error response.


Login and obtain access token
-----------------------------

:ref:`Once configured <settings-openid>`, the OpenID configuration details are provided in the capabilities object at the :ref:`root URL <api-utilities-hello>`:

.. code-block:: http
    :emphasize-lines: 11-16

    HTTP/1.1 200 OK
    Content-Length: 638
    Content-Type: application/json

    {
        "capabilities": {
            "openid": {
                "description": "OpenID connect support.",
                "providers": [
                    {
                        "name": "google",
                        "auth_path": "/openid/google/login",
                        "client_id": "XXXXX.apps.googleusercontent.com",
                        "header_type": "Bearer",
                        "issuer": "https://accounts.google.com",
                        "userinfo_endpoint": "https://www.googleapis.com/oauth2/v3/userinfo"
                    }
                ],
                "url": "http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html"
            }
        }
    }

In order to initiate the login and its browser redirections (aka. «dance»), just reach the URL specified in the ``auth_path``
for the configured provider ``name``.

::

    GET /openid/{name}/login?callback={URI}&scope={scope}

- ``callback`` which is the URI the browser will be redirected to after the login (eg. ``http://dashboard.myapp.com/#tokens=``).
  It will be suffixed with the JSON response from the :term:`Identity Provider`, which will either be the access and ID tokens or an error.
- ``scope`` which should at least be ``openid`` (but usually ``openid email``) (see your Identity Provider documentation)

.. note::

    Because multiple OpenID providers can be enabled on the server, the ``auth_path`` URI contains the provider name with which the login process is initiated (eg. client initiates login by redirecting to ``/openid/auth0/login?...`` or ``/openid/google/login?...`` etc.)


JavaScript example
------------------

Let's go through a simple OpenID login example using the :github:`JavaScript kinto client <Kinto/kinto-http.js>`.

When the user clicks a login button, it initiates the login process by redirecting the browser to the
Identity Provider, which itself redirects it to the application page once successful.

.. code-block:: JavaScript
    :emphasize-lines: 12,15,19-25

    const KINTO_URL = 'http://localhost:8888/v1';

    const SCOPES = 'openid email';

    // Redirect to the same page using the location hash.
    const CALLBACK_URL = window.location.href + '#tokens=';

    const kintoClient = new KintoClient(KINTO_URL);

    document.addEventListener('DOMContentLoaded', async () => {
      // Initiate login on some button click
      loginBtn.addEventListener('click', login);

      // Check if the location contains the tokens (after being redirected)
      const authResult = parseToken();
      if (authResult) {
        const {access_token, token_type} = authResult;
        if (access_token) {
          // Set access token for requests to Kinto.
          kintoClient.setHeaders({
            'Authorization': `${token_type} ${access_token}`,
          });
          // Show if Kinto authenticates me:
          const {user} = await kintoClient.fetchServerInfo();
          alert("You are " + (user ? user.id : "unknown"));
        }
        else {
          console.error('Authentication error', authResult);
        }

      }
    });

The ``login()`` function is straightforward:

.. code-block:: JavaScript

    function login() {
      const {capabilities: {openid: {providers}}} = await kintoClient.fetchServerInfo();
      // Use the first configured provider
      const {auth_path} = providers[0];
      // Redirect the browser to the authentication page.
      const callback = encodeURIComponent(CALLBACK_URL);
      window.location = `${KINTO_URL}${auth_path}?callback=${callback}&scope=${SCOPES}`;
    }

The ``parseToken()`` function scans the location hash to read the Identity Provider response:

.. code-block:: JavaScript

    function parseToken() {
      const hash = decodeURIComponent(window.location.hash);
      const tokensExtract = /tokens=([.\s\S]*)/.exec(hash);
      if (!tokensExtract) {
        // No token in URL bar.
        return null;
      }
      const tokens = tokensExtract[1];
      const parsed = JSON.parse(tokens);
      return parsed;
    }

Check out the :github:`full demo source code <leplatrem/kinto-oidc-demo>`.


Example of login redirections
-----------------------------

Let's assume the JavaScript app is accessible on http://localhost:3000 and the Kinto server running on http://localhost:8888.

When the user clicks the login button, the browser will follow a sequence of redirections similar to this one:

#. User clicks on the ``auth0`` login button
#. JavaScript redirects to `<http://localhost:8888/v1/openid/auth0/login?scope=openid email&callback=http://localhost:3000/#provider=auth0&tokens=>`_
#. Kinto generates and stores a *state* string
#. Kinto redirects to Auth0 that will show the login form `<https://minimal-demo-iam.auth0.com/authorize?client_id=BXqGVgl2meRsdVK0dEZPTk516JUhje2M&response_type=code&scope=openid+email&redirect_uri=http://localhost:8888/v1/openid/auth0/token?&state=3a309f5baba>`_
#. User enters credentials and authenticates
#. Auth0 redirects to Kinto with the *state* and a *code* `<http://localhost:8888/v1/openid/auth0/token?code=lWpsu9VoHLJEVyy1&state=3a309f5baba>`_
#. Kinto checks that the *state* matches
#. Kinto trades the *code* against the ID and Access tokens
#. Kinto redirects back to the Single Page App appending the JSON encoded ID and Access tokens to the callback URL provided at step 2 `<http://localhost:3000/#provider=auth0&tokens={"access_token":"tY6um989...jfcer","id_token":"eyJ0eXAiOiJ...KV1QiL.ojkhgwRVH...UG8JGRENNF.Es8...DK10","expires_in":86400,"token_type":"Bearer"}>`_
#. JavaScript code parses the location hash and reads the ID and Access tokens

The JavaScript app can now use the Access token to make authenticated calls to the Kinto server, and read the user info from the ID token fields. See :github:`demo <leplatrem/kinto-oidc-demo>`.
