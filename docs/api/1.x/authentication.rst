##############
Authentication
##############

.. _authentication:

Kinto is an API, and uses the request headers to authenticate the current user.

Based on the authentication enabled in configuration, Kinto will authenticate the user and assign a :term:`user identifier` to the request (eg. ``ldap:alice@corp``).

Since authentication is entirely pluggable in Kinto (see :ref:`configuration <configuration-authentication>`), the HTTP method used to authenticate requests may vary.
But the main methods you are most likely to encounter will read the ``Authorization`` header. For example:

* :ref:`Kinto Accounts <api-accounts>` expects a valid username and password as *Basic Auth*
* :ref:`OpenID Connect <api-openid>` will validate a *Bearer Access Token* against an :term:`Identity Provider`


Getting started
---------------

If you are familiar with OpenID Connect, then jump to the :ref:`dedicated section <api-openid>`.

Otherwise, the easiest way to get started with Kinto is probably to use :ref:`internal Kinto accounts <api-accounts>` which work the usual way: users sign-up with username and password. In this case, authentication is as simple as:

::

    Authorization: Basic <string>

where ``<string>`` is the result of ``base64("username:password")``.


Try authentication
------------------

The currently authenticated *user ID* can be obtained on the :ref:`root URL <api-utilities-hello>`. If the ``"user"`` field is not returned, this means that the authentication was not successful.

.. code-block:: bash

    $ http GET https://kinto.dev.mozaws.net/v1/ --auth admin:s3cr3t

.. code-block:: http
    :emphasize-lines: 6

    HTTP/1.1 200 OK

    {
        "url": "https://kinto.dev.mozaws.net/v1/",
        "user": {
            "bucket": "4399ed6c-802e-3278-5d01-44f261f0bab4",
            "id": "account:admin",
            "principals": [
                "account:admin",
                "system.Everyone",
                "system.Authenticated"
            ]
        }
        ...
    }


Error responses
---------------

As shown in the above section, the easiest way to check your authentication credentials is to use the :ref:`root URL <api-utilities-hello>`.

When authentication fails when interacting with API, you can have two kinds of error responses:

* a |status-401| error response, which means that no authentication method succeeded
* a |status-403| error response, which could mean that the operation performed on the resource is not allowed for you :) If you didn't authenticate, this could also mean that the operation is not allowed to anonymous users.


Available methods
-----------------

In order to know which authentication methods are supported by a *Kinto* server, you can query the :ref:`root URL <api-utilities-hello>` and check the ``"capabilities"`` field.

.. code-block:: shell

    $ http https://kinto.dev.mozaws.net/v1/

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Content-Length, Alert
    Connection: keep-alive
    Content-Length: 2561
    Content-Type: application/json
    Date: Mon, 24 Sep 2018 15:12:51 GMT
    Server: nginx
    X-Content-Type-Options: nosniff

    {
        "capabilities": {
            "accounts": {
                "description": "Manage user accounts.",
                "url": "https://kinto.readthedocs.io/en/latest/api/1.x/accounts.html"
            },
            "basicauth": {
                "description": "Very basic authentication sessions. Not for production use.",
                "url": "http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html"
            },
            "openid": {
                "description": "OpenID connect support.",
                "providers": [
                    {
                        "auth_path": "/openid/auth0/login",
                        "client_id": "XNmXEZhGfNaYltbCKustGunTbH0r8Gkp",
                        "header_type": "Bearer",
                        "issuer": "https://auth.mozilla.auth0.com/",
                        "name": "auth0",
                        "userinfo_endpoint": "https://auth.mozilla.auth0.com/userinfo"
                    }
                ],
                "url": "http://kinto.readthedocs.io/en/stable/api/1.x/authentication.html"
            },
            "portier": {
                "description": "Authenticate users using Portier.",
                "url": "https://github.com/Kinto/kinto-portier",
                "version": "0.2.0"
            }
        }
    }


For example, :github:`Kinto Admin <Kinto/kinto-admin>` inspects that list in order to dynamically offer several authentication options in its login form.


Permissions
-----------

In order to control which users are allowed to create or modify objects, we mention their user IDs in permissions or groups members.

For more details, check :ref:`the permissions section of the documention <api-principals>`.
