.. _authenticating:

Authenticating to the Kinto API
###############################

A word about users with Kinto
=============================

First of all Kinto doesn't handle users management.

There is no such thing as user sign-up, password modification, etc.

However, since Kinto handle permissions on objects, users are uniquely
identified.

If you are wondering how it is possible, you probably want to read
the explanation about :ref:`authenticating with Kinto <authenticating>`.


How is that possible?
---------------------

This is possible by plugging in Kinto with an Identity provider.

Multiple identity providers solutions are available such as OAuth,
SAML, x509, Hawk sessions, JWT, or Basic Auth tokens.

With regards to the application you are building you may want to plug
Github, Facebook, Google, or your company identity provider.

In these documentation examples we will use a Basic Authentication,
which computes a user id based on the token provided in the request.

This method has many limitations but has the advantage to avoid
specific setup or third-party services to get started immediately.

When using arbitrary tokens make sure that:

 - each user has a different one;
 - a user always uses the same token.


How can we generate strong unique tokens?
-----------------------------------------

We recommand you to use at least a 16 random bytes strings such as an UUID:

Using the ``uuidgen`` cli tool:

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

Then you can use:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/ \
        --auth "token:6f8dfa43-668c-4e5c-89bc-eaabcb866342"

And observe the user ID in the response.


How Kinto knows it is a valid Basic Auth token?
-----------------------------------------------

For each token, Kinto will calculate a unique user ID which is
related to your Kinto instance ``user_hmac_secret`` configuration.

.. note::

    Two Kinto instances using the same ``user_hmac_secret`` will
    generate the same user ID for a given Basic Auth token.

You can get the :term:`user ID` generated for your token on the Kinto hello page:

.. code-block:: shell

    $ http https://kinto.dev.mozaws.net/v1/ --auth "token:my-secret"

.. code-block:: json
    :emphasize-lines: 24

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Connection: keep-alive
    Content-Length: 498
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 29 Jan 2016 09:13:33 GMT
    Server: nginx

    {
        "cliquet_protocol_version": "2", 
        "http_api_version": "1.0", 
        "project_docs": "https://kinto.readthedocs.org/", 
        "project_name": "kinto", 
        "project_version": "1.10.0", 
        "settings": {
            "attachment.base_url": "https://kinto.dev.mozaws.net/attachments/", 
            "batch_max_requests": 25, 
            "cliquet.batch_max_requests": 25, 
            "readonly": false
        }, 
        "url": "https://kinto.dev.mozaws.net/v1/", 
        "user": {
            "bucket": "e777874f-2936-11a1-3269-68a6c1648a92", 
            "id": "basicauth:c635be9375673027e9b2f357a3955a0a46b58aeface61930838b61e946008ab0"
        }
    }

As soon as this user ID is used to give permission on an object
(buckets, groups, collections, records), the user will be grant that
permission using the token.


How can I change the token for a given user?
--------------------------------------------

Asking yourself this question is a first sign that you should not be
using the Basic Auth authentication backend for your use case.

Because the user ID is calculated from the token, changing the token
will change the user ID.

You can generate other user IDs based on other tokens and give
permissions to them.

You can even create a group that could handle all the available tokens
for a given user, and change the token once for all without having to
change the permission of each object.

You can generate new tokens and give the ``write`` permission to their
respective user id.

You can also create a group per « user » whose members are the different
user IDs obtained from tokens. And then use this group in permission
definitions on objects.

Most likely, you would use an identity provider which will be in
charge of user and token management (generate, refresh, validate,
...). `See this example with Django <http://django-oauth-toolkit.readthedocs.org/en/latest/tutorial/tutorial_01.html>`_.

You can also read our
:ref:`tutorial about how to plug the Github authorisation backend <tutorial-github>`.
