##############
Authentication
##############

.. _authentication:


Depending on the authentication policies initialized in the application,
the HTTP method to authenticate requests may differ.

A policy based on *OAuth2 bearer tokens* is recommended, but not mandatory.

A *Basic Auth* can also be enabled in :ref:`configuration` for the convenience
of clients or testing.

By default, we profite a setup using :term:`Firefox Accounts`, that verifies
the *OAuth2 bearer tokens* on a remote server, and provides some API endpoints
to perform the *OAuth* dance.


Basic Auth
==========

If enabled in settings, using a *Basic Auth* token will associate a unique
user id for any username/password combination.

::

    Authorization: Basic <basic_token>


The token is built using this formula ``base64("username:password")``.

:notes:

    If not enabled (**default**) this will result in a ``401`` error response.


OAuth Bearer token
==================

Use the OAuth token with this header:

::

    Authorization: Bearer <oauth_token>


:notes:

    If the token is not valid, this will result in a ``401`` error response.


Firefox Account
===============

Obtain the token
----------------

Using the Web UI
::::::::::::::::

* Navigate the client to ``GET /v1/fxa-oauth/login?redirect=http://app-endpoint/#``. There, a session
  cookie will be set, and the client will be redirected to a login
  form on the FxA content server
* After submitting the credentials on the login page, the client will
  be redirected to ``http://app-endpoint/#{token}`` the web-app.


Custom flow
:::::::::::

The ``GET /v1/fxa-oauth/params`` endpoint can be use to get the
configuration in order to trade the Firefox Account BrowserID with a
Bearer Token. `See Firefox Account documentation about this behavior
<https://developer.mozilla.org/en-US/Firefox_Accounts#Firefox_Accounts_BrowserID_API>`_

.. code-block:: http

    $ http GET http://localhost:8000/v0/fxa-oauth/params -v

    GET /v0/fxa-oauth/params HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Host: localhost:8000
    User-Agent: HTTPie/0.8.0


    HTTP/1.1 200 OK
    Content-Length: 103
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 19 Feb 2015 09:28:37 GMT
    Server: waitress

    {
        "client_id": "89513028159972bc",
        "oauth_uri": "https://oauth-stable.dev.lcip.org",
        "scope": "profile"
    }
