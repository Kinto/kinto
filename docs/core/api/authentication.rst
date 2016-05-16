##############
Authentication
##############

.. _authentication:


Depending on the authentication policies initialized in the application,
the HTTP method to authenticate requests may differ.

A policy based on *OAuth2 bearer tokens* is recommended, but not mandatory.
See :ref:`configuration <configuration-authentication>` for further
information.

In the current implementation, when multiple policies are configured,
:term:`user identifiers` are isolated by policy. In other words, there is no way to
access the same set of records using different authentication methods.

By default, a relatively secure *Basic Auth* is enabled.

Basic Auth
==========

If enabled in configuration, using a *Basic Auth* token will associate a unique
:term:`user identifier` to an username/password combination.

::

    Authorization: Basic <basic_token>

The token shall be built using this formula ``base64("username:password")``.

Empty passwords are accepted, and usernames can be anything (custom, UUID, etc.)

If the token has an invalid format, or if *Basic Auth* is not enabled,
this will result in a ``401`` error response.

.. warning::

    Since :term:`user id` is derived from username and password, there is no way
    to change the password without loosing access to existing records.


OAuth Bearer token
==================

If the configured authentication policy uses *OAuth2 bearer tokens*, authentication
shall be done using this header:

::

    Authorization: Bearer <oauth_token>


The policy will verify the provided *OAuth2 bearer token* on a remote server.

:notes:

    If the token is not valid, this will result in a ``401`` error response.


Firefox Accounts
================

In order to enable authentication with :term:`Firefox Accounts`, install and
configure :github:`mozilla-services/kinto-fxa`.
