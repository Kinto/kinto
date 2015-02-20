##############
Authentication
##############

.. _authentication:

Cliquet uses FirefoxAccounts as an authentication. The recommended way to
connect to Firefox Accounts is via an OAuth flow. This is the default and
preffered way to authenticate to Cliquet servers.

Of course, it's possible to plug other authentication policies, all the Pyramid
authentication policies will work.

Firefox Account OAuth Bearer token
==================================

Use the OAuth token with this header:

::

    Authorization: Bearer <oauth_token>

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


Basic Auth
==========

In addition to OAuth, *Basic Auth* can be enabled in the configuration using
``cliquet.basic_auth_backdoor = true``.

Articles will then be stored for any username/password combination provided.
