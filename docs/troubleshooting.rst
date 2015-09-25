Troubleshooting
###############

.. _troubleshooting:

We are doing the best we can so you do not have to read this section.

In case you do, please find the common problems you may have below.

If you do not find your problem here, please file an issue or ask for
help on `#storage <http://chat.mibbit.com/?server=irc.mozilla.org&channel=#storage>`_


Module object has no attribute 'register_json'
==============================================

Kinto uses PostgreSQL ``JSONBin`` feature, which allow Kinto to
efficiently store ``JSON objects`` into PostgreSQL, support for which
was added to PostgreSQL in version 9.4.

This is a hard requirement for postgresql backends, therefore you
will either need to **use PostgreSQL 9.4 (or greater)**, or
:ref:`use a different backend <configuration-backends>` entirely.
