If the object is missing (or already deleted), a |status-404| is returned only
if the user has `write` access to the object parent, otherwise a |status-403|
is returned to avoid leaking information about non-accessible objects.
The consumer might decide to ignore it.

If the ``If-Match`` request header is provided, and if the object has
changed meanwhile, a |status-412| error is returned.

.. note::

    Once deleted, an object will appear in the list when polling for changes,
    with a deleted status (``delete=true``) and will have most of its fields empty.
