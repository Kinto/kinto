.. _error-responses:

###############
Error responses
###############

API description
===============

Every response is JSON.

If the HTTP status is not OK (<200 or >=400), the response contains a JSON mapping, with the following attributes:

- ``code``: matches the HTTP status code (e.g ``400``)
- ``errno``: stable application-level error number (e.g. ``109``)
- ``error``: string description of error type (e.g. ``"Bad request"``)
- ``message``: context information (e.g. ``"Invalid request parameters"``)
- ``info``: online resource (e.g. URL to error details)
- ``details``: additional details (e.g. list of validation errors)

**Example response**

::

    {
        "code": 412,
        "errno": 114,
        "error": "Precondition Failed",
        "message": "Resource was modified meanwhile",
        "info": "https://server/docs/api.html#errors",
    }


Refer yourself to the :ref:`set of errors codes <errors>`.


Retry-After indicators
======================

A ``Retry-After`` header will be added to error responses (>=500),
telling the client how many seconds it should wait before trying
again.

::

    Retry-After: 30

.. _error-responses-precondition:

Precondition errors
===================

As detailed in the :ref:`timestamps  <server-timestamps>` section, it is
possible to add concurrency control using ``ETag`` request headers.

When a the provided preconditions are not met, a |status-412| error response
is returned.

Additional information about the record currently stored on the server will be
provided in the ``details`` field:

::

    {
        "code": 412,
        "errno": 114,
        "error":"Precondition Failed"
        "message": "Resource was modified meanwhile",
        "details": {
            "existing": {
                "last_modified": 1436434441550,
                "id": "00dd028f-16f7-4755-ab0d-e0dc0cb5da92",
                "title": "Original title"
            }
        },
    }


Validation errors
=================

When multiple validation errors occur on a request, the first one is presented
in the message.

The full list of validation errors is provided in the ``details`` field.

::

    {
        "code": 400,
        "errno": 109,
        "error": "Bad Request",
        "message": "Invalid posted data",
        "info": "https://server/docs/api.html#errors",
        "details": [
            {
                "description": "42 is not a string: {'name': ''}",
                "location": "body",
                "name": "name"
            }
        ]
    }


Conflict errors
===============

When concurrent requests are manipulating the same resource, it can happen that
some database transactions overlap and end up as integrity constraint violations.

In this case, a |status-409| error response is returned. Retrying the same request
will usually be enough to get over it.

::

    {
        "code": 409,
        "errno": 122,
        "error": "Conflict",
        "message": "Integrity constraint violated, please retry.",
    }
