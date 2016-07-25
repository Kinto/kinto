Validation and conflicts behaviour is similar to creating objects (``POST``).

If the ``If-Match: "<timestamp>"`` request header is provided as described in
the :ref:`section about timestamps <server-timestamps>`, and if the object has
changed meanwhile, a |status-412| error is returned.

If the ``If-None-Match: *`` request header is provided  and if there is already
an existing object with this ``id``, a |status-412| error is returned.

Permissions
-----------

In the JSON request payloads, at least one of ``data`` and ``permissions`` must be provided. Permissions can thus be replaced independently from data.

In the case of creation, if only ``permissions`` is provided, an empty object is created.

The :ref:`current user id <api-current-userid>` **is always added** among the ``write`` principals.

See :ref:`api-permissions-payload`.
