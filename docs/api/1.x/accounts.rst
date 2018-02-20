.. _api-accounts:

Accounts
########

When the built-in plugin ``kinto.plugins.accounts`` is enabled in configuration,
it becomes possible to manage accounts via a new resource ``/accounts``.

Via this endpoint, users can sign-up, modify their password or delete their account.
Administrators configured in settings can manage users accounts.

.. _accounts-setup:

Setup
=====

Add the following settings to the ``.ini`` file:

.. code-block:: ini

    # Enable built-in plugin.
    kinto.includes = kinto.plugins.accounts

    # Enable authenticated policy.
    multiauth.policies = account
    multiauth.policy.account.use = kinto.plugins.accounts.authentication.AccountsAuthenticationPolicy

    # Allow anyone to create accounts.
    kinto.account_create_principals = system.Everyone

    # Set the session time to live in seconds
    kinto.account_cache_ttl_seconds = 30


You can use the ``create-user`` command to create an admin:

.. code-block:: bash

    kinto create-user --ini /etc/kinto.ini --username admin --password ThisIsN0tASecurePassword

You can then use it in your config:

.. code-block:: ini

    # Allow anyone to create accounts.
    kinto.account_create_principals = account:admin
    kinto.account_write_principals = account:admin

	
.. _accounts-auth:

Authentication
==============

Accounts are defined using a username and a password, and uses *Basic Authentication*.

For example, once the ``bob`` account has been created, you can check if authentication
works using the :ref:`Hello view <api-utilities>`.

.. sourcecode:: bash

    $ http GET http://localhost:8888/v1/ --auth bob:azerty123

.. sourcecode:: http

    GET /v1/ HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic Ym9iOmF6ZXJ0eTEyMw==
    Connection: keep-alive
    Host: localhost:8888
    User-Agent: HTTPie/0.9.8

.. sourcecode:: http
    :emphasize-lines: 25-26

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Alert, Backoff, Content-Length, Retry-After
    Content-Length: 448
    Content-Type: application/json
    Date: Tue, 21 Mar 2017 14:40:14 GMT
    Server: waitress
    X-Content-Type-Options: nosniff

    {
        "capabilities": {
            "accounts": {
                "description": "Manage user accounts.",
                "url": "http://kinto.readthedocs.io/en/latest/api/1.x/accounts.html"
            }
        },
        "http_api_version": 1.16,
        "project_docs": "https://kinto.readthedocs.io/",
        "project_name": "kinto",
        "project_version": "6.1.0.dev0",
        "settings": {
            "batch_max_requests": 25,
            "readonly": false
        },
        "url": "http://localhost:8888/v1/",
        "user": {
            "id": "account:bob",
            "principals": [
                "account:bob",
                "system.Everyone",
                "system.Authenticated"
            ]
        }
    }


.. _accounts-create:

Create account
==============

.. http:put:: /accounts/(user_id)

    :synopsis: Creates a new account.

    **Anonymous**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"password": "azerty123"}}' | http PUT http://localhost:8888/v1/accounts/bob --verbose

    .. sourcecode:: http

        PUT /v1/accounts/bob HTTP/1.1
        Accept: application/json, */*
        Accept-Encoding: gzip, deflate
        Connection: keep-alive
        Content-Length: 36
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.8

        {
            "data": {
                "password": "azerty123"
            }
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Content-Length, Alert
        Content-Length: 165
        Content-Type: application/json
        Date: Tue, 21 Mar 2017 14:30:14 GMT
        Etag: "1490106614601"
        Last-Modified: Tue, 21 Mar 2017 14:30:14 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {
            "data": {
                "id": "bob",
                "last_modified": 1490106614601,
                "password": "$2b$12$zlTlYet5v.v57ak2gEYyoeqKSGzLvwXF/.v3DGpT/q69LecHv68gm"
            },
            "permissions": {
                "write": [
                    "account:bob"
                ]
            }
        }


Alternatively, accounts can be created using POST.  Supply the user id and password in the request body and remove user id from the URL.  The following request is equivalent to the example PUT call:

    .. sourcecode:: bash

        $ echo '{"data": {"id": "bob", password": "azerty123"}}' | http POST http://localhost:8888/v1/accounts --verbose


By default, users can only create their own accounts. "Administrators", meaning anyone who matches ``account_write_principals``, can create accounts for other users as well.

You can set ``account_create_principals`` if you want to limit account creation to certain users. The most common situation is when you want to have a small number of administrators, who are responsible for creating accounts for other users. In this case, you should add the administrators to both ``account_create_principals`` and ``account_write_principals``.

.. _accounts-udpate:

Change password
===============

.. http:put:: /accounts/(user_id)

    :synopsis: Changes the password for an existing account.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"password": "azerty123"}}' | http PUT http://localhost:8888/v1/accounts/bob --verbose --auth 'bob:azerty123'

    .. sourcecode:: http

        PUT /v1/accounts/bob HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOmF6ZXJ0eTEyMw==
        Connection: keep-alive
        Content-Length: 36
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {
                "password": "azerty123"
            }
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Alert, Content-Length, Retry-After
        Content-Length: 165
        Content-Type: application/json
        Date: Tue, 21 Mar 2017 17:11:58 GMT
        Etag: "1490116321096"
        Last-Modified: Tue, 21 Mar 2017 17:12:01 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {
            "data": {
                "id": "bob",
                "last_modified": 1490116321096,
                "password": "$2b$12$c12ui4O/z9gmVpGe1NMG2.Sb4zdw9p20oka2Seg3Xqq9rDpNR5HoW"
            },
            "permissions": {
                "write": [
                    "account:bob"
                ]
            }
        }


.. _accounts-delete:

Delete account
==============

.. http:delete:: /accounts/(user_id)

    :synopsis: Deletes an existing account.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http DELETE http://localhost:8888/v1/accounts/bob --verbose --auth 'bob:azerty123'

    .. sourcecode:: http

        DELETE /v1/accounts/bob HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOmF6ZXJ0eTEyMw==
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Alert, Content-Length, Retry-After
        Content-Length: 66
        Content-Type: application/json
        Date: Tue, 21 Mar 2017 17:18:14 GMT
        Etag: "1490116696859"
        Last-Modified: Tue, 21 Mar 2017 17:18:16 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {
            "data": {
                "deleted": true,
                "id": "bob",
                "last_modified": 1490116696859
            }
        }


.. _accounts-manage:

Manage accounts
===============

It is possible to configure administrators in settings. They will be able to manage
others users accounts via the API.

First create the actual accounts:

::

    $ echo '{"data": {"password": "azerty123"}}' | http PUT http://localhost:8888/v1/accounts/admin

Then mention the created accounts via the following settings in the ``.ini`` file.
For example to account IDs ``admin`` and members of the ``admin`` groups in the ``bid`` bucket:

.. code-block:: ini

    # Give read/write access to all accounts to ``account:admin``.
    kinto.account_write_principals = account:admin /buckets/bid/groups/admin
    kinto.account_read_principals = account:admin /buckets/bid/groups/admin

.. note::

    It is not very convenient to require a server restart for configuring administrators.
    But we thought it was acceptable as a first iteration.
