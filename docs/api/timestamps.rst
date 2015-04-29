.. _server-timestamps:

#################
Server timestamps
#################

The ``Last-Modified`` header with the current timestamp of the collection for
the current user will be given on collection and record GET endpoints.

::

    Last-Modified: 1422375916186


In order to bypass costly and error-prone HTTP date parsing, timestamps are
not true HTTP date values.

Timestamps are **milliseconds** EPOCH timestamps,

In order to avoid race conditions, *Cliquet* guarantees that each change will
increment the timestamp of the related collection.
If two changes happen at the same millisecond, they will still have two differents
timestamps.
