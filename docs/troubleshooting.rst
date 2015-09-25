Troubleshooting
###############

.. _troubleshooting:

We are doing the best we can so you do not have to read this section.

In case you do, please find the common problems you may have below.

If you do not find your problem here, please file an issue or ask for
help on `#storage <http://chat.mibbit.com/?server=irc.mozilla.org&channel=#storage>`_


Module object has no attribute 'register_json'
==============================================

This means the PostgreSQL server you are talking to does not support
the JSON features kinto postgresql backend is counting on.

You should **upgrade your PostgreSQL server to version 9.4** or higher.

You can also :ref:`configure another backend <configuration-backends>`.
