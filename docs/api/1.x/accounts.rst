.. _api-accounts:

Accounts
########

When the built-in plugin ``kinto.plugins.accounts`` is enabled in configuration,
it becomes possible to manage accounts via a new resource ``/accounts``.

.. important::

    This plugin is **highly experimental**


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


.. _accounts-udpate:

Change password
===============

*TO BE DOCUMENTED*


.. _accounts-delete:

Delete account
==============

*TO BE DOCUMENTED*


.. _accounts-manage:

Manage accounts
===============

* Configure administrator in ``.ini`` settings

*TO BE DOCUMENTED*
