
If the ``If-Match: "<timestamp>"`` request header is provided as described in
the :ref:`section about timestamps <server-timestamps>`, and if the list has
changed meanwhile, a |status-412| error is returned.

If the ``If-None-Match: *`` request header is provided, and if the provided ``data``
contains an ``id`` field, and if there is already an existing object with this ``id``,
a |status-412| error is returned.

.. important::

    If the posted object has an ``id`` field, it will be taken into account.

    However, if a object already exists with the same ``id``, a |status-200| response
    is returned with the existing object in body (instead of |status-201|).
    See https://github.com/Kinto/kinto/issues/140


Validation
----------

If the posted values are invalid (e.g. *field value is not an integer*)
an error response is returned with |status-400|.

See :ref:`details on error responses <error-responses>`.


Permissions
-----------

In the JSON request payloads, an optional ``permissions`` attribute can be provided.

The :ref:`current user id <api-current-userid>` **is always added** among the ``write`` principals.

See :ref:`api-permissions-payload`.

.. Feature of Kinto.core not used in Kinto

.. Conflicts
.. ---------

.. Since some fields can be defined as unique per collection, some conflicts
.. may appear when creating records.

.. .. note::

..     Empty values are not taken into account for field unicity.

.. .. note::

..     Deleted records are not taken into account for field unicity.

.. If a conflict occurs, an error response is returned with status |status-409|.
.. A ``details`` attribute in the response provides the offending record and
.. field name. See :ref:`dedicated section about errors <error-responses>`.
