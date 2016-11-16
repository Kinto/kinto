If the object is missing (or already deleted), a |status-404| is returned only
if the user has `write` access to the object parent, otherwise a |status-403|
is returned to avoid leaking information about non-accessible objects.
The consumer might decide to ignore it.

If the ``If-Match: "<timestamp>"`` request header is provided as described in
the :ref:`section about timestamps <server-timestamps>`, and if the object has
changed meanwhile, a |status-412| error is returned.

.. note::

    ``last_modified`` is updated to the current server timestamp, only if a
    field value was changed.


Attributes merge
----------------

The provided values are merged with the existing object. For example:

* ``{"a":"b"}`` + ``{"a":"c"}`` → ``{"a":"c"}``
* ``{"a":"b"}`` + ``{"b":"c"}`` → ``{"a":"b", "b":"c"}``
* ``{"a":"b"}`` + ``{"a":null}`` → ``{"a":null}`` : *attributes can't be removed with patch*
* ``{"a": {"b":"c"}}`` + ``{"a":{"d":"e"}}`` → ``{"a":{"d":"e"}}`` : *sub-objects are replaced, not merged*

`JSON merge <https://tools.ietf.org/html/rfc7396>`_
is currently supported using ``Content-Type: application/merge-patch+json``. This provides
support to merging sub-objects and removing attibutes. For example:

* ``{"a":"b"}`` + ``{"a":null}`` → ``{}``
* ``{"a": {"b":"c"}}`` + ``{"a":{"d":"e"}}`` → ``{"a":{"b:c", "d":"e"}}``
* ``{}`` + ``{"a":{"b":{"c":null}}}`` → ``{"a":{"b":{}}}``

Light response body
-------------------

If a ``Response-Behavior`` request header is set to ``light``,
only the fields whose value was changed are returned. If set to
``diff``, only the fields whose value became different than
the one provided are returned.

Permissions
-----------

In the JSON request payloads, at least one of ``data`` and ``permissions`` must be provided. Permissions can thus be modified independently from data.

The :ref:`current user id <api-current-userid>` **is always added** among the ``write`` principals.

See :ref:`api-permissions-payload`.

..
.. Kinto.core feature, not used in Kinto:
..
.. Read-only fields
.. ----------------

.. If a read-only field is modified, a |status-400| error is returned.

JSON Patch Operations
---------------------

`JSON-Patch <https://tools.ietf.org/html/rfc6902>`_ is a way to define a sequence
of operations to be applied on a JSON object.

It's possible to use JSON-Patch by sending the request header ``Content-Type: application/json-patch+json``.

When using this request header, the body should contain a list of operations,
for example:

.. code-block:: javascript

    [
        { "op": "test", "path": "data/a", "value": "foo" },
        { "op": "remove", "path": "/data/a" },
        { "op": "add", "path": "/data/b", "value": [ "foo", "bar" ] },
        { "op": "replace", "path": "/data/b", "value": 42 },
        { "op": "move", "from": "/data/a", "path": "/data/c" },
        { "op": "copy", "from": "/data/b", "path": "/data/d" }
    ]

For more information about each operation, please refer to
`JSON-Patch Specification <https://tools.ietf.org/html/rfc6902>`_.

This is very useful when altering permissions since there is no need to get
the current value before adding some principal to the list. Value is not used
on permission operations and can be omitted.

.. code-block:: javascript

    [
        { "op": "test", "path": "/permissions/read/fxa:alice" },
        { "op": "add", "path": "/permissions/read/system.Everyone" },
        { "op": "remove", "path": "/permissions/read/fxa:bob" }
    ]
