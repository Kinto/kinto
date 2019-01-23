.. _api-openid:
.. _authentication-openid:

OpenID Connect
==============

OpenID relies on *OAuth2 bearer tokens*, so basically authentication shall be done using this header:

::

    Authorization: Bearer <access_token>

.. note::

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
- ``prompt`` (optional) if set has to be the word ``none``. Generally used for Silent Authentication.

.. note::

    Because multiple OpenID providers can be enabled on the server, the ``auth_path`` URI contains the provider name with which the login process is initiated (eg. client initiates login by redirecting to ``/openid/auth0/login?...`` or ``/openid/google/login?...`` etc.)

.. note::

    The effect of adding ``&prompt=none`` tells the Identity Provider to not present a ``200 OK`` response. Only redirects.

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
      const tokens = atob(tokensExtract[1]);
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
#. Kinto redirects back to the Single Page App appending the JSON encoded ID and Access tokens to the callback URL provided at step 2 `<http://localhost:3000/#provider=auth0&tokens=eyJhY2Nlc3NfdG9rZW4iOiJ0WTZ1bTk4OS4uLmpmY2VyIiwiaWRfdG9rZW4iOiJleUowZVhBaU9pSi4uLktWMVFpTC5vamtoZ3dSVkguLi5VRzhKR1JFTk5GLkVzOC4uLkRLMTAiLCJleHBpcmVzX2luIjo4NjQwMCwidG9rZW5fdHlwZSI6IkJlYXJlciJ9>`_
#. JavaScript code parses the location hash and reads the ID and Access tokens

The JavaScript app can now use the Access token to make authenticated calls to the Kinto server, and read the user info from the ID token fields. See :github:`demo <leplatrem/kinto-oidc-demo>`.
