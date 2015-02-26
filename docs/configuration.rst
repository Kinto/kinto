.. _configuration:

Configuration
#############


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
    # cliquet.delete_collection_enabled = true


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

Basic Auth
::::::::::

.. code-block :: ini

    # cliquet.basic_auth_enabled = true
    # cliquet.userid_hmac_secret = b4c96a8692291d88fe5a97dd91846eb4


Custom Authentication
:::::::::::::::::::::

Is is possible to overwrite the Cliquet initialization in order to replace
the default authentication backend.

Internally, Cliquet relies on Pyramid ``authenticated_userid`` request
attribute to associate users to records.


.. code-block :: python

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize_cliquet(config, __version__)

        config.include('velruse.providers.github')


Or set it up manually:

.. code-block :: python

    import pyramid_multiauth

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize_cliquet(config, __version__)

        policies = [
            cliquet.authentication.BasicAuthAuthenticationPolicy(),
            myproject.authentication.MyPolicy()
        ]
        authn_policy = pyramid_multiauth.MultiAuthenticationPolicy(policies)

        config.set_authentication_policy(authn_policy)


Firefox Account
:::::::::::::::

As `stated in the official documentation <https://developer.mozilla.org/en-US/Firefox_Accounts>`_,
Firefox Accounts OAuth integration is currently limited to Mozilla relying services.

If you're a Mozilla service, fill the settings with the values you were provided:

.. code-block :: ini

    fxa-oauth.client_id = 89513028159972bc
    fxa-oauth.client_secret = 9aced230585cc0aaea0a3467dd800
    fxa-oauth.oauth_uri = https://oauth-stable.dev.lcip.org
    fxa-oauth.scope = profile
