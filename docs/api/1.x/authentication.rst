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

Depending on your use case, you may want to plug Github, Facebook, Google, or your
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

You can also read our :ref:`tutorial about how to plug the Github authorisation backend <tutorial-github>`.


OAuth Bearer token
==================

If the configured authentication policy uses *OAuth2 bearer tokens*, authentication
shall be done using this header:

::

    Authorization: Bearer <oauth_token>


The policy will verify the provided *OAuth2 bearer token* on a remote server.

:notes:

    If the token is not valid, this will result in a |status-401| error response.


Firefox Accounts
----------------

In order to enable authentication with :term:`Firefox Accounts`, install and
configure :github:`mozilla-services/kinto-fxa`.
