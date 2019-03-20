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

Details about accounts configuration are given in :ref:`the settings section <settings-accounts>`.

Basically, you can check if the ``accounts`` feature is enabled if it is mentioned in the ``"capabilities"`` field on the :ref:`root URL <api-utilities-hello>`.


.. _accounts-auth:

Authentication
==============

Accounts are defined using a username and a password, and uses *Basic Authentication*.

For example, once the ``bob`` account has been created (see below), you can check if authentication
works using the :ref:`root URL <api-utilities-hello>`.

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

        $ echo '{"data": {"id": "bob", "password": "azerty123"}}' | http POST http://localhost:8888/v1/accounts --verbose

.. note::

    Depending on the :ref:`configuration <settings-accounts>`, you may not be allowed to create accounts.

.. note::

    If the :ref:`accounts validation <settings-account-validation>` is enabled,
    you might also need to provide an ``email-context`` in the ``data``: 

    .. sourcecode:: bash

        $ echo '{"data": {"id": "bob@example.com", "password": "azerty123", "email-context": {"name": "Bob Smith", "form-url": "https://example.com/validate/"}}}' | http POST http://localhost:8888/v1/accounts --verbose


.. _accounts-update:

Change password
===============

.. http:put:: /accounts/(user_id)

    :synopsis: Changes the password for an existing account.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"password": "qwerty123"}}' | http PUT http://localhost:8888/v1/accounts/bob --verbose --auth 'bob:azerty123'

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
                "password": "qwerty123"
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
others users accounts.

For example, create somebody else account:

::

    $ echo '{"data": {"id": "sam-body", "password": "else"}}' | http POST http://localhost:8888/v1/accounts --auth admin:s3cr3t

List accounts:

::

    $ http GET http://localhost:8888/v1/accounts --auth admin:s3cr3t


Or delete some account:

::

    $ http DELETE http://localhost:8888/v1/accounts/sam-body --auth admin:s3cr3t



.. _accounts-validate:

Validate accounts
=================

When the ``account_validation`` option is enabled in :ref:`the settings
<settings-account-validation>`, account IDs need to be valid email addresses:
they need to match the regexp in the ``account_validation.email_regexp``
setting. The default one is very generic, but you may restrict it to only allow
certain emails, for example only ones from a specific domain.

To make sure the ``account_validation`` is enabled, you can check if the
``validation_enabled`` flag is ``true`` in the ``"accounts"`` field on the
:ref:`root URL <api-utilities-hello>`.

.. http:post:: /accounts/(user_id)/validate/(activation_key)

    :synopsis: Activates a newly created account with the ``account_validation`` option enabled.

    **Anonymous**

    **Example Request**

    .. sourcecode:: bash

        $ http POST http://localhost:8888/v1/accounts/bob@example.com/validate/2fe7a389-3556-4c8f-9513-c26bfc5f160b --verbose


    .. sourcecode:: http

        POST /v1/accounts/bob@example.com/validate/2fe7a389-3556-4c8f-9513-c26bfc5f160b HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.8

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Content-Length, Retry-After, Backoff, Alert
        Content-Length: 195
        Content-Type: application/json
        Date: Mon, 21 Jan 2019 13:41:17 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {
            "id": "bob@example.com",
            "last_modified": 1548077982793,
            "password": "$2b$12$zlTlYet5v.v57ak2gEYyoeqKSGzLvwXF/.v3DGpT/q69LecHv68gm",
            "validated": true
        }

.. _accounts-reset-password:

Resetting a forgotten password
==============================

If the ``account_validation`` option in :ref:`the settings
<settings-account-validation>` has been enabled, a temporary reset password may
be requested through the endpoint available at ``/accounts/(user
id)/reset-password``.

.. http:post:: /accounts/(user_id)/reset-password

    :synopsis: Request a temporary reset password for an account with the ``account_validation`` option enabled.

    **Anonymous**

    **Example Request**

    .. sourcecode:: bash

        $ http POST http://localhost:8888/v1/accounts/bob@example.com/reset-password --verbose


    .. sourcecode:: http

        POST /v1/accounts/bob@example.com/reset-password HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.8


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Alert, Retry-After, Content-Length
        Content-Length: 62
        Content-Type: application/json
        Date: Fri, 08 Feb 2019 14:04:15 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {
            "message": "A temporary reset password has been sent by mail"
        }

   .. note::

       You might also need to provide an ``email-context`` in the ``data`` to fill
       in the holes of the email template defined in the :ref:`settings
       <settings-account-password-reset>`:

       .. sourcecode:: bash

          $ echo '{"data": {"email-context": {"name": "Bob Smith"}}}' | http POST http://localhost:8888/v1/accounts/bob@example.com/reset-password --verbose

Using this temporary reset password, one can
:ref:`update the account <accounts-update>` providing the new password.
