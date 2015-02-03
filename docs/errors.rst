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

+-------------+-------+------------------------------------------------+
| status code | errno | description                                    |
+-------------+-------+------------------------------------------------+
| 401         | 104   | Missing Authorization Token                    |
+-------------+-------+------------------------------------------------+
| 401         | 105   | Invalid Authorization Token                    |
+-------------+-------+------------------------------------------------+
| 400         | 106   | request body was not valid JSON                |
+-------------+-------+------------------------------------------------+
| 400         | 107   | invalid request parameter                      |
+-------------+-------+------------------------------------------------+
| 400         | 108   | missing request parameter                      |
+-------------+-------+------------------------------------------------+
| 400         | 109   | invalid posted data                            |
+-------------+-------+------------------------------------------------+
| 404         | 110   | Invalid Token / id                             |
+-------------+-------+------------------------------------------------+
| 404         | 111   | Missing Token / id                             |
+-------------+-------+------------------------------------------------+
| 403         | 121   | Resource's access forbidden for this user      |
+-------------+-------+------------------------------------------------+
| 409         | ?     | Another resource violates constraint           |
+-------------+-------+------------------------------------------------+
| 411         | 112   | Content-Length header was not provided         |
+-------------+-------+------------------------------------------------+
| 412         | 114   | Resource was modified meanwhile                |
+-------------+-------+------------------------------------------------+
| 413         | 113   | Request body too large                         |
+-------------+-------+------------------------------------------------+
| 429         | 117   | Client has sent too many requests              |
+-------------+-------+------------------------------------------------+
| 500         | 999   | Internal Server Error                          |
+-------------+-------+------------------------------------------------+
| 503         | 201   | Service Temporary unavailable due to high load |
+-------------+-------+------------------------------------------------+
| 5??         | 202   | Client version too old                         |
+-------------+-------+------------------------------------------------+
| 513         | ?     | Service Decommissioned                         |
+-------------+-------+------------------------------------------------+


Validation errors
=================

In case multiple validation errors occurs on requests, there will be
returned one at the time.
