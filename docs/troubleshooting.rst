Troubleshooting
###############

.. _troubleshooting:

We are doing the best we can so you do not have to read this section.

That said, we have included solutions (or at least explanations) for
some common problems below.

If you do not find a solution to your problem here, please
:ref:`ask for help <communication_channels>`!


Module object has no attribute 'register_json'
==============================================

Kinto uses the ``JSONBin`` feature of PostgreSQL, which is used to
store native ``JSON objects`` efficiently. Support for this feature
was added in PostgreSQL 9.4.

This is a hard requirement for postgresql backends, therefore you
will either need to **use PostgreSQL 9.4 (or greater)**, or
:ref:`use a different backend <configuration-backends>` entirely.
