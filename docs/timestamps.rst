#################
Server timestamps
#################

.. _server-timestamps:

In order to avoid race conditions, all timestamps manipulated by the server are
not true HTTP date values, nor milliseconds EPOCH timestamps.

They are milliseconds EPOCH timestamps with the guarantee of a change per timestamp update.
If two changes happen at the same millisecond, they will have two differents timestamps.

The ``Last-Modified`` header with the last timestamp of the collection for a given
user will be given on collection and record GET endpoints.

::

    Last-Modified: 1422375916186

:note:
    Both fields ``added_on`` and ``marked_on`` will contain actual timestamps
    (from device perspective), used for calendar year information display.

All timestamp of the app will be set in milliseconds.
