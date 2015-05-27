##############
Authentication
##############

.. _authentication:


Depending on the authentication policies initialized in the application,
the HTTP method to authenticate requests may differ.

A policy based on *OAuth2 bearer tokens* is recommended, but not mandatory.

A *Basic Auth* can also be enabled in :ref:`configuration <configuration-authentication>`.

In the current implementation, when multiple policies are configured,
:term:`user identifiers` are isolated by policy. In other words, there is no way to
access the same set of records using different authentication methods.


Basic Auth
==========

If enabled in configuration, using a *Basic Auth* token will associate a unique
:term:`user identifier` to an username/password combination.

::

    Authorization: Basic <basic_token>

The token shall be built using this formula ``base64("username:password")``.

Empty passwords are accepted, and usernames can be anything (UUID, etc.)

If the token has an invalid format, or if *Basic Auth* is not enabled,
this will result to a ``401`` error response.

.. warning::

    Since :term:`user id` is derived from username and password, there is no way
    to change the password without loosing access to existing records.


OAuth Bearer token
==================

If the configured authentication policy uses OAuth2 bearer tokens, authentication
shall be done using this header:

::

    Authorization: Bearer <oauth_token>


The policy will verify the provided *OAuth2 bearer token* on a remote server.

:notes:

    If the token is not valid, this will result in a ``401`` error response.


Firefox Account
===============

Currently, the default authentication relies on :term:`Firefox Accounts`, but any
-:ref:`authentication backend supported by Pyramid can be used <configuration-authentication>`.

By default, if no policy is configured, a policy for :term:`Firefox Accounts` is
setup.

Obtain the token
----------------

Using the Web UI
::::::::::::::::

If *OAuth Relier* endpoints are enabled :ref:`in configuration <configuration-authentication>`,
this policy provides some API endpoints to perform the *OAuth* dance, and
obtain the token using HTTP redirections.

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
