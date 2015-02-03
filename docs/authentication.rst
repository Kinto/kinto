##############
Authentication
##############

.. _authentication:

Use the OAuth token with this header:

::

    Authorization: Bearer <oauth_token>

**Obtain the token**

* Navigate the client to ``GET /v1/fxa-oauth/login?redirect=http://app-endpoint``. There, a session
  cookie will be set, and the client will be redirected to a login
  form on the FxA content server
* After submitting the credentials on the login page, the client will
  be redirected to ``http://app-endpoint`` the web-app should then
  access ``GET /v1/fxa-oauth/token``, where its session will be
  validated. Then, an OAuth token will be returned inside a JSON
  object:

::

    {
        "token": "oihyvuh-fefe-ldpieo98963fyhrn"
    }

**Reading list scope**

The *reading list* API will eventually have to handle a dedicated OAuth scope (e.g.
``readinglist``, ``readinglist:read``, ``readinglist:write``). This will help users
to delegate access to the readinglist to third party apps

So far the FxA server only handles the ``profile`` scope.

See https://github.com/mozilla-services/readinglist/issues/16.
