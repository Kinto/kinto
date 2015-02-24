Configuration
#############

.. _configuration:

See `Pyramid settings documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/environment.html>`_.


Project info
============

.. code-block :: ini

    cliquet.project_name = project
    cliquet.project_docs = https://project.rtfd.org/

Feature settings
================

.. code-block :: ini

    # cliquet.batch_max_requests = 25


Deployment
==========

.. code-block :: ini

    # cliquet.backoff = 10
    cliquet.http_scheme = https
    cliquet.retry_after = 30
    cliquet.eos =

Storage
=======

.. code-block :: ini

    cliquet.session_backend = cliquet.session.redis
    cliquet.storage_backend = cliquet.storage.redis
    cliquet.storage_url = redis://localhost:6379/1

See :ref:`storage backend documentation <storage>` for more details.


Authentication
==============

.. code-block :: ini

    # cliquet.basic_auth_backdoor = true
    # cliquet.userid_hmac_secret = b4c96a8692291d88fe5a97dd91846eb4

    fxa-oauth.client_id = 89513028159972bc
    fxa-oauth.client_secret = 9aced230585cc0aaea0a3467dd800
    fxa-oauth.oauth_uri = https://oauth-stable.dev.lcip.org
    fxa-oauth.scope = profile
