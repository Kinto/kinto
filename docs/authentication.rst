##############
Authentication
##############

.. _authentication:

Firefox Account OAuth Bearer token
==================================

Use the OAuth token with this header:

::

    Authorization: Bearer <oauth_token>

**Obtain the token**

* Navigate the client to ``GET /v1/fxa-oauth/login?redirect=http://app-endpoint/#``. There, a session
  cookie will be set, and the client will be redirected to a login
  form on the FxA content server
* After submitting the credentials on the login page, the client will
  be redirected to ``http://app-endpoint/#{token}`` the web-app.

**Reading list scope**

The *Reading List* API will eventually have to handle a dedicated OAuth scope (e.g.
``readinglist``, ``readinglist:read``, ``readinglist:write``). This will help users
to delegate access to the *Reading List* to third party apps

So far the FxA server only handles the ``profile`` scope.

See https://github.com/mozilla-services/readinglist/issues/16.


Basic Auth
==========

In addition to OAuth, *Basic Auth* can be enabled in the configuration using
``readinglist.basic_auth_backdoor = true``.

Articles will then be stored for any username/password combination provided.
