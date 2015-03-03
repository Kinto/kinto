###############
Error responses
###############

.. _error-responses:

Protocol description
====================

Every response is JSON.

If the HTTP status is not OK (<200 or >=400), the response contains a JSON mapping, with the following attributes:

- ``code``: matches the HTTP status code (e.g ``400``)
- ``errno``: stable application-level error number (e.g. ``109``)
- ``error``: string description of error type (e.g. ``"Bad request"``)
- ``message``: context information (e.g. ``"Invalid request parameters"``)
- ``info``: additional details (e.g. URL to error details)

**Example response**

::

    {
        "code": 400,
        "errno": 109,
        "error": "Bad Request",
        "message": "Invalid posted data",
        "info": "https://server/docs/api.html#errors"
    }

Error codes
===========

Errors are meant to be managed at the project level.

However, a basic ref:`<set of errors codes <errors>`_ is provided in cliquet.

Validation errors
=================

In case multiple validation errors occur on a request, they will be
returned one at a time.
