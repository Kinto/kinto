.. _settings:

Settings
########

.. image:: /images/overview-features.png
    :align: center

If you are looking for installation instructions, please refer to :ref:`install`.

Kinto is built to be highly configurable. As a result, the related
configuration can be verbose, but don't worry, all configuration flags are
listed below.


.. _configuration-environment:

Environment variables
=====================

In order to ease deployment or testing strategies, *Kinto* reads settings
from environment variables, in addition to ``.ini`` files.

The environment variables are exactly the same as the settings, but they
are capitalised and ``.`` are replaced by ``_``.

For example, ``kinto.storage_backend`` is read from environment variable
``KINTO_STORAGE_BACKEND`` (if defined of course).

All settings are read first from the environment variables, then from
application ``.ini``, and finally from internal defaults.


.. _configuration-features:

Feature settings
================

+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| Setting name                                    | Default      | What does it do?                                                          |
+=================================================+==============+===========================================================================+
| kinto.readonly                                  | ``False``    | If set to true, the whole service will reject every write operation.      |
|                                                 |              | Note that with this option, the ``default`` bucket cannot be used and     |
|                                                 |              | request will be rejected with a |status-405| error response.              |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.batch_max_requests                        | ``25``       | The maximum number of requests that can be sent to the batch endpoint.    |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.paginate_by                               | ``None``     | The maximum number of items to include on a response before enabling      |
|                                                 |              | pagination. If set to ``None``, no pagination will be used.               |
|                                                 |              | It is recommended to set-up pagination if the server is under high load.  |
|                                                 |              | If not defined, a collection response cannot contain                      |
|                                                 |              | more elements than defined by the                                         |
|                                                 |              | ``kinto.storage_max_fetch_size`` setting.                                 |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.<object-type>_id_generator                | ``UUID4``    | The Python *dotted* location of the generator class that should be used   |
|                                                 |              | to generate identifiers on a POST endpoint.                               |
|                                                 |              | Object type is one of ``bucket``, ``collection``, ``group``, ``record``.  |
|                                                 |              | See :ref:`tutorial-id-generator`.                                         |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.experimental_collection_schema_validation | ``False``    | *Experimental*: Allow definition of JSON schema at the collection level,  |
|                                                 |              | in order to :ref:`validate submitted records <collection-json-schema>`.   |
|                                                 |              | It is marked as experimental because the API might be subject to changes. |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.experimental_permissions_endpoint         | ``False``    | *Experimental*: Add a new ``/permissions`` endpoint to let the user grab  |
|                                                 |              | the list of objects (buckets, collections, groups, records) on which they |
|                                                 |              | have read or write permission.                                            |
|                                                 |              | It is marked as experimental because the API might be subject to changes. |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.trailing_slash_redirect_enabled           | ``True``     | Try to redirect resources removing slash or adding it for the root URL    |
|                                                 |              | endpoint: ``/v1`` redirects to ``/v1/`` and ``/buckets/default/``         |
|                                                 |              | to ``/buckets/default``. No redirections are made when turned off.        |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+
| kinto.heartbeat_timeout_seconds                 | ``10``       | The maximum duration of each heartbeat entry, in seconds.                 |
+-------------------------------------------------+--------------+---------------------------------------------------------------------------+

.. note::

    ``kinto.readonly`` will disable every endpoint that is not accessed with one of
    ``GET``, ``OPTIONS``, or ``HEAD`` HTTP methods. Requests will receive a
    |status-405| error response.

    The cache backend will still needs read-write privileges, in order to
    cache OAuth authentication states and tokens for example.


.. _configuration-backends:

Backends
========

Kinto relies on three types of backends: storage, cache and permission. The
settings names have a different prefix for each.

For each of them, the supported services are currently PostgreSQL, Redis, and Memory.
Memcached is also available as a cache backend.

Storage
:::::::

+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| Setting name                 | Default                       | What does it do?                                                         |
+==============================+===============================+==========================================================================+
| kinto.storage_backend        | ``kinto.core.storage.memory`` | The Python *dotted* location of the storage backend to use.              |
|                              |                               |                                                                          |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_url            | ``''``                        | The URL to use to authenticate to the storage backend. e.g.              |
|                              |                               | ``redis://localhost:6378/1`` or ``postgresql://user:pass@database/db``   |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_max_fetch_size | ``10000``                     | The maximum number of items that can be returned by one request to the   |
|                              |                               | storage backend. If no pagination is enabled, this is the maximum number |
|                              |                               | of items that can be stored in a collection (otherwise some of them      |
|                              |                               | won't be returned). With pagination enabled, this limitation doesn't     |
|                              |                               | apply.                                                                   |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_pool_size      | ``25``                        | The size of the pool of connections to use for the storage backend.      |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_max_overflow   | ``5``                         | Number of connections that can be opened beyond pool size.               |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_pool_recycle   | ``-1``                        | Recycle connections after the given number of seconds has passed.        |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_pool_timeout   | ``30``                        | Number of seconds to wait before giving up on getting a connection from  |
|                              |                               | the pool.                                                                |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_max_backlog    | ``-1``                        | Number of threads that can be in the queue waiting for a connection.     |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    kinto.storage_backend = kinto.core.storage.postgresql
    kinto.storage_url = postgresql://postgres:postgres@localhost/postgres

    # Safety limit while fetching from storage
    # kinto.storage_max_fetch_size = 10000

    # Control number of pooled connections
    # kinto.storage_pool_size = 50


Cache
:::::

+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| Setting name               | Default                     | What does it do?                                                             |
+============================+=============================+==============================================================================+
| kinto.cache_backend        | ``kinto.core.cache.memory`` | The Python *dotted* location of the cache backend to use.                    |
|                            |                             |                                                                              |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_url            | ``''``                      | The URL to use to authenticate to the cache backend. e.g.                    |
|                            |                             | ``redis://localhost:6378/1`` or ``postgresql://user:pass@database/db``       |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_prefix         | ``''``                      | A prefix added to each key. Useful when having multiple Kinto using the same |
|                            |                             | cache database.                                                              |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_max_size_bytes | ``524288``                  | The maximum size the memory cache backend will allow per process. (in bytes) |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_pool_size      | ``25``                      | The size of the pool of connections to use for the cache backend.            |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_max_overflow   | ``5``                       | Number of connections that can be opened beyond pool size.                   |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_pool_recycle   | ``-1``                      | Recycle connections after the given number of seconds has passed.            |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_pool_timeout   | ``30``                      | Number of seconds to wait before giving up on getting a connection from      |
|                            |                             | the pool.                                                                    |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_max_backlog    | ``-1``                      | Number of threads that can be in the queue waiting for a connection.         |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_hosts          | ``''``                      | The space separated list of Memcached hosts.                                 |
+----------------------------+-----------------------------+------------------------------------------------------------------------------+

**For PostgreSQL**

.. code-block:: ini

    kinto.cache_backend = kinto.core.cache.postgresql
    kinto.cache_url = postgresql://postgres:postgres@localhost/postgres

    # Control number of pooled connections
    # kinto.cache_pool_size = 50


For **Memcached**

You would need to install the memcached dependencies: ``pip install kinto[memcached]``

.. code-block:: ini

    kinto.cache_backend = kinto.core.cache.memcached
    kinto.cache_hosts = 127.0.0.1:11211 127.0.0.2:11211

Permissions
:::::::::::

+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| Setting name                   | Default                          | What does it do?                                                         |
+================================+==================================+==========================================================================+
| kinto.permission_backend       | ``kinto.core.permission.memory`` | The Python *dotted* location of the permission backend to use.           |
|                                |                                  |                                                                          |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_url           | ``''``                           | The URL to use to authenticate to the permission backend. e.g.           |
|                                |                                  | ``redis://localhost:6379/1``                                             |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_pool_size     | ``25``                           | The size of the pool of connections to use for the permission backend.   |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_max_overflow  | ``5``                            | Number of connections that can be opened beyond pool size.               |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_pool_recycle  | ``-1``                           | Recycle connections after the given number of seconds has passed.        |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_pool_timeout  | ``30``                           | Number of seconds to wait before giving up on getting a connection from  |
|                                |                                  | the pool.                                                                |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_max_backlog   | ``-1``                           | Number of threads that can be in the queue waiting for a connection.     |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    kinto.permission_backend = kinto.core.permission.postgresql
    kinto.permission_url = postgresql://postgres:postgres@localhost/postgres

    # Control number of pooled connections
    # kinto.permission_pool_size = 50

Bypass permissions with configuration
:::::::::::::::::::::::::::::::::::::

Permissions are usually retrieved from the permission backend. However, it is
also possible to configure them from settings, and it will **bypass** the
permission backend.

For example, for a resource named "bucket", the following setting will enable
authenticated people to create bucket records:

.. code-block:: ini

    kinto.bucket_create_principals = system.Authenticated

The format of these permission settings is
``<resource_name>_<permission>_principals = comma,separated,principals``.


Scheme, host, and port
======================

By default, Kinto relies on WSGI for underlying details like host, port, or
request scheme. Tuning these settings may be necessary when the application
runs behind proxies or load balancers, but most implementations
(such as uWSGI) provide adequate values automatically.

That said, if ever these items need to be controlled at the application layer,
the following settings are available:

Check the behaviour of the server with the ``url`` value returned in :ref:`the
hello view <api-utilities>`.

+-------------------+----------+--------------------------------------------------------------------------+
| Setting name      | Default  | What does it do?                                                         |
+===================+==========+==========================================================================+
| kinto.http_host   | ``None`` | The HTTP Host used by Kinto to refer to itself. If set to `None`, the    |
|                   |          | HTTP host is read from HTTP headers or WSGI environment.                 |
+-------------------+----------+--------------------------------------------------------------------------+
| kinto.http_scheme | ``None`` | The HTTP scheme used by Kinto to refer to itself. If set to `None`, the  |
|                   |          | HTTP scheme is read from the HTTP headers or WSGI environment.           |
+-------------------+----------+--------------------------------------------------------------------------+

.. code-block :: ini

   # kinto.http_scheme = https
   # kinto.http_host = production.server.com:7777


Logging and Monitoring
======================

+------------------------+----------------------------------------+--------------------------------------------------------------------------+
| Setting name           | Default                                | What does it do?                                                         |
+========================+========================================+==========================================================================+
| kinto.statsd_backend   | ``kinto.core.statsd``                  | The Python **dotted** location of the StatsD module that should be used  |
|                        |                                        | for monitoring. Useful to plug custom implementations like Datadog™.     |
+------------------------+----------------------------------------+--------------------------------------------------------------------------+
| kinto.statsd_prefix    | ``kinto``                              | The prefix to use when sending data to statsd.                           |
+------------------------+----------------------------------------+--------------------------------------------------------------------------+
| kinto.statsd_url       | ``None``                               | The fully qualified URL to use to connect to the statsd host. e.g.       |
|                        |                                        | ``udp://localhost:8125``                                                 |
+------------------------+----------------------------------------+--------------------------------------------------------------------------+

Standard Logging
::::::::::::::::

With the following configuration, all logs are redirected to standard output
(See `12factor app <http://12factor.net/logs>`_):

.. code-block:: ini

    [loggers]
    keys = root

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = DEBUG
    handlers = console

    [handler_console]
    class = StreamHandler
    args = (sys.stdout,)
    level = NOTSET
    formatter = generic

    [formatter_generic]
    format = %(asctime)s,%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s
    datefmt = %H:%M:%S

Example output:

::

    16:18:57,179 INFO  [root] Running kinto 6.1.0.dev0.
    16:19:00,729 INFO  [request.summary]
    16:19:22,232 WARNI [kinto.core.authorization] Permission not granted.
    16:19:22,238 INFO  [request.summary]


Colored Logging
:::::::::::::::

.. code-block:: ini

    [formatters]
    keys = color

    [formatter_color]
    class = logging_color_formatter.ColorFormatter

Example output:

.. image:: ../images/color-formatter.png


JSON Logging
::::::::::::

Using a JSON logging formatter, like :github:`this one <mozilla/mozilla-cloud-services-logger>`,
it is possible to output logs as JSON:

.. code-block:: ini

    [formatters]
    keys = json

    [formatter_json]
    class = kinto.core.JsonLogFormatter


Example output:

::

    {"Pid": 19240, "Type": "root", "Timestamp": 1489067815875679744, "Severity": 6, "Hostname": "pluo", "Logger": "%", "EnvVersion": "2.0", "Fields": {"message": "Running kinto 6.1.0.dev0."}}
    {"Pid": 19240, "Type": "root", "Timestamp": 1489067817834153984, "Severity": 4, "Hostname": "pluo", "Logger": "%", "EnvVersion": "2.0", "Fields": {"perm": "read", "userid": "ldap:john@corp.com", "message": "Permission not granted.", "uri": "/buckets/123"}}


Handling exceptions with Sentry
:::::::::::::::::::::::::::::::

Requires the ``raven`` package.

Sentry logging can be enabled `as explained in official documentation
<https://raven.readthedocs.io/en/latest/integrations/pyramid.html#logger-setup>`_.

.. note::

    The application sends an *INFO* message on startup (mainly for setup check).


Monitoring with StatsD
::::::::::::::::::::::

Requires the ``statsd`` package.

StatsD metrics can be enabled (disabled by default):

.. code-block:: ini

    kinto.statsd_url = udp://localhost:8125
    # kinto.statsd_prefix = kinto-prod


Monitoring with New Relic
:::::::::::::::::::::::::

Requires the ``newrelic`` package.

+-----------------------+----------+--------------------------------------------------------------------------+
| Setting name          | Default  | What does it do?                                                         |
+=======================+==========+==========================================================================+
| kinto.newrelic_config | ``None`` | Location of the newrelic configuration file.                             |
+-----------------------+----------+--------------------------------------------------------------------------+
| kinto.newrelic_env    | ``dev``  | The environment the server runs into                                     |
+-----------------------+----------+--------------------------------------------------------------------------+

New Relic can be enabled (disabled by default):

.. code-block:: ini

    kinto.newrelic_config = /location/of/newrelic.ini
    kinto.newrelic_env = prod


.. _configuration-plugins:

Plugins
=======

It is possible to extend the default Kinto behaviors by using "plugins".

The list of plugins to load at startup can be specified in the settings, as a
list of Python modules:

.. code-block:: ini

    kinto.includes = kinto.plugins.default_bucket
                     kinto.plugins.history
                     kinto.plugins.admin
                     kinto-attachment
                     custom-myplugin

+---------------------------------------+--------------------------------------------------------------------------+
| Built-in plugins                      | What does it do?                                                         |
+=======================================+==========================================================================+
| ``kinto.plugins.accounts``            | It allows users to sign-up and authenticate using username and password  |
|                                       | (:ref:`more details <api-accounts>`).                                    |
+---------------------------------------+--------------------------------------------------------------------------+
| ``kinto.plugins.admin``               | It is a Web admin UI to manage data from a Kinto server.                 |
|                                       | (:ref:`more details <kinto-admin>`).                                     |
+---------------------------------------+--------------------------------------------------------------------------+
| ``kinto.plugins.default_bucket``      | It enables a personal bucket ``default``, where collections are created  |
|                                       | implicitly (:ref:`more details <buckets-default-id>`).                   |
+---------------------------------------+--------------------------------------------------------------------------+
| ``kinto.plugins.flush``               | Adds an endpoint to completely remove all data from the database backend |
|                                       | for testing/staging purposes. (:ref:`more details <api-flush>`).         |
+---------------------------------------+--------------------------------------------------------------------------+
| ``kinto.plugins.history``             | It tracks every action performed on objects within a bucket              |
|                                       | (:ref:`more details <api-history>`).                                     |
+---------------------------------------+--------------------------------------------------------------------------+
| ``kinto.plugins.openid``              | It allows to authenticate users using OpenID Connect from Google,        |
|                                       | Microsoft, Auth0, etc. (:ref:`more details <api-openid>`).               |
+---------------------------------------+--------------------------------------------------------------------------+
| ``kinto.plugins.quotas``              | It allows to limit storage per collection size, number of records, etc.  |
|                                       | (:ref:`more details <api-quotas>`).                                      |
+---------------------------------------+--------------------------------------------------------------------------+


There are `many available packages`_ in Pyramid ecosystem, and it is straightforward to build one,
since the specified module must just define an ``includeme(config)`` function.

.. _many available packages: https://github.com/ITCase/awesome-pyramid

See `our list of community plugins <https://github.com/Kinto/kinto/wiki/Plugins>`_.

See also: :ref:`tutorial-write-plugin` for more in-depth informations on how
to create your own plugin.


Pluggable components
::::::::::::::::::::

:term:`Pluggable` components can be substituted from configuration files,
as long as the replacement follows the original component API.

.. code-block:: ini

    kinto.logging_renderer = your_log_renderer.CustomRenderer

This is the simplest way to extend *Kinto*, but will be limited to its
existing components (cache, storage, log renderer, ...).

In order to add extra features, including external packages is the way to go!


.. _configuration-authentication:

Authentication
==============

Kinto authentication mechanism is entirely pluggable. We call them :term:`authentication policies`.

It is possible to enable several authentication policies. **The order matters**: when multiple policies are configured, the first one in the list that succeeds is picked.

**The name matters**: the policy name that is picked will be used as the prefix of the :term:`user ID` (eg. ``ldap:alice``).

+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+
| Setting name                   | Default                                               | What does it do?                                                         |
+================================+=======================================================+==========================================================================+
| multiauth.policies             | `` ``                                                 | The list of authentication policies names that are enabled.              |
|                                |                                                       | Each policy is configured using dedicated settings as explained          |
|                                |                                                       | below.                                                                   |
+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+
| multiauth.authorization_policy | ``kinto.authorization.AuthorizationPolicy``           | Python *dotted* path the authorization policy to use for the permission  |
|                                |                                                       | mecanism.                                                                |
+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+


Authentication setup
::::::::::::::::::::

Any authentication policy can be specified through configuration. The list of names in ``multiauth.policies`` is the starting point for *Kinto* to read the respective parameters (``multiauth.policy.{name}.*`` settings).

.. code-block:: ini

    multiauth.policies = google
    multiauth.policy.google.use = kinto.plugins.openid.OpenIDConnectPolicy
    multiauth.policy.google.issuer = https://accounts.google.com
    multiauth.policy.google.client_id = 42XXXX365001.apps.googleusercontent.com
    multiauth.policy.google.client_secret = UAlL-054uyh5in4b6u8jhg5o3hnj

.. _settings-accounts:

Accounts
::::::::

With the built-in :ref:`accounts plugin <api-accounts>`, users can sign-up and authenticate with username and password.

A common setup would be the following:

* Anyone can create accounts
* A specific ``admin`` can manage them all

.. code-block:: ini

    # Enable built-in plugin.
    kinto.includes = kinto.plugins.accounts

    # Enable authenticated policy.
    multiauth.policies = account
    multiauth.policy.account.use = kinto.plugins.accounts.AccountsPolicy

    # Allow anyone to create accounts.
    kinto.account_create_principals = system.Everyone

    # Set the session time to live in seconds
    kinto.account_cache_ttl_seconds = 30

You can use the ``create-user`` command to create an admin:

.. code-block:: bash

    $ kinto create-user --ini /etc/kinto.ini --username admin --password ThisIsN0tASecurePassword

You can then use this ``account:admin`` in your config:

.. code-block:: ini

    # Allow anyone to create accounts.
    kinto.account_create_principals = system.Everyone
    # But also allow the admin to update, delete them etc.
    kinto.account_write_principals = account:admin

**About account management**

You can set ``account_create_principals`` if you want to limit account creation to certain users. The most common situation is when you want to have a small number of administrators, who are responsible for creating accounts for other users. In this case, you should add the administrators to both ``account_create_principals`` and ``account_write_principals``.

.. code-block:: ini

    kinto.account_create_principals = account:admin ldap:jack@corp.com /buckets/bid/groups/admin
    kinto.account_write_principals = account:admin ldap:jack@corp.com /buckets/bid/groups/admin

See the :ref:`API docs <api-accounts>` to create accounts, change passwords etc.

.. _settings-account-validation:

**About account validation**

You can enable the :ref:`account validation <accounts-validate>` option, which
will require account IDs to be valid email addresses, to which a validation
email will be sent with an activation key.

.. code-block:: ini

    kinto.account_validation = true
    # Mail configuration:
    # Set the sender for the validation email.
    kinto.account_validation.email_sender = "admin@example.com"

.. note::

    Both the account validation and password reset need a properly configured
    SMTP server.
    To use a debug or testing mailer you may use the ``mail.mailer = debug`` or
    ``mail.mailer = testing`` settings. Refer to
    `pyramid_mailer's configuration <https://docs.pylonsproject.org/projects/pyramid_mailer/en/latest/#configuration>`_.

You can restrict the email addresses allowed using the
``account_validation.email_regexp`` setting, and the delay for which the
activation key will be valid:

.. code-block:: ini

    # Set the regular expression used to validate a proper email address.
    kinto.account_validation.email_regexp = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
    # Set the "time to live" for the activation key stored in the cache. After that
    # delay the account won't be activable anymore.
    kinto.account_validation.validation_key_cache_ttl_seconds = 604800  # 7 days in seconds.

Once :ref:`created <accounts-create>`, the account will need to be
:ref:`activated <accounts-validate>` before being able to authenticate, using
the ``validate`` endpoint and the ``activation-key`` sent by email.

If the user was created, an email was sent to the user with the activation key,
which needs to be POSTed to the ``validate`` endpoint.

Example email:

::

    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: quoted-printable
    From: admin@example.com
    Subject: activate your account
    To: bob@example.com
    Content-Disposition: inline

    2fe7a389-3556-4c8f-9513-c26bfc5f160b

It is the responsability of the administrator to tell the mail recipient how to
validate the account by modifying the email body template in the settings.

This could be done by providing a link to a webapp that displays a form to the
user with a call to action to validate the user, which will POST the activation
key to the ``validate`` endpoint.

Or the email could explain how to copy the activation code and paste it in some
settings window.

The templates for the email subject and body can be customized:

.. code-block:: ini

    kinto.account_validation.email_subject_template = "Account activation"
    kinto.account_validation.email_body_template = "Hello {id},\n you can now activate your account using the following link:\n {form-url}{activation-key}"

... and they will be ``String.format``-ted with the content of the user, an
optional additional ``email-context`` provided alongside the user object, and
the ``activation-key`` (see the note in :ref:`account creation
<accounts-create>` for an example usage).

Whatever the means, a POST to the
``/accounts/(user_id)/validate/(activation_key)`` will validate and activate
the user.

Once the account is validated, another email will be sent for confirmation,
rendered using the same ``email-context``.

.. code-block:: ini

    kinto.account_validation.email_confirmation_subject_template = "Account active"
    kinto.account_validation.email_confirmation_body_template = "Your account {id} is now active"

.. _settings-account-password-reset:

**About password reset**

When the :ref:`account validation <accounts-validate>` option is enabled, an
additional endpoint is available at ``/accounts/(user id)/reset-password`` to
require a temporary reset password by email (see :ref:`the API docs
<accounts-reset-password>`).

Example email sent to the user with the temporary reset password:

::

    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: quoted-printable
    From: admin@example.com
    Subject: Reset password
    To: mathieu@agopian.info
    Content-Disposition: inline

    b8ae48e6-709e-4f01-bfb9-bca9464cdcfc

The template used for the email subject and body can be customized using the
following settings:

.. code-block:: ini

    kinto.account_validation.email_reset_password_subject_template = "Temporary reset password for {id}"
    kinto.account_validation.email_reset_password_body_template = "Hello {id},\n you can use the following temporary reset password to change your password\n{reset-password}"

Those templates will be rendered using the user record fields, an optional
additional ``email-context`` provided alongside the user object, and the
``reset-password`` (see the note in :ref:`resetting a forgotten password
<accounts-reset-password>` for an example usage).


It is the responsability of the administrator to tell the mail recipient how to
change their password using this temporary password.

This could be done by providing a link to a webapp that displays a form to the
user asking for the new password and a call to action, which will POST the
new password to the ``accounts/(user_id)`` endpoint.

Using this temporary reset password, one can
:ref:`update the account <accounts-update>` providing the new password.

This temporary reset password will be valid for the amount of seconds set in
the settings:

.. code-block:: ini

    # Set the "time to live" for the reset password stored in the cache.
    kinto.account_validation.reset_password_cache_ttl_seconds = 604800  # 7 days in seconds.

.. _settings-openid:

OpenID Connect
::::::::::::::

First of all, you must find an Identity Provider. Google Identity Platform for example, but it may also be Auth0, Microsoft, Yahoo, Paypal, Bitbucket, Ebay, Salesforce, ... or whichever platform that publishes its discovery metadata as JSON.

The ``google`` name below was chosen arbitrarily. As stated above, it will become the user ID prefix (e.g. ``google:someuser@gmail.com``) and will appear in the OAuth authorized redirect URL.

While setting up the Identity Provider, you might have to fill some URLs related to your Kinto instance. For example, if you run a single page app on ``localhost:3000`` that interacts with a server on ``localhost:8888``, you should set:

- *Authorized JavaScript origins*: ``http://localhost:3000``
- *Authorized redirect URIs* (aka. *callback*): ``http://localhost:8888/v1/openid/google/token?``

.. note::

    If you use the :ref:`Kinto Admin plugin <kinto-admin>`, the *JavaScript origin* will be the same as the server (eg. ``http://localhost:8888``) since the Admin Web page is served by the server itself.

Based on the information obtained during this setup, configure the ``issuer``, ``client_id`` and ``client_secret`` values in Kinto settings:

.. code-block:: ini

    kinto.includes = kinto.plugins.openid

    multiauth.policies = google
    multiauth.policy.google.use = kinto.plugins.openid.OpenIDConnectPolicy
    multiauth.policy.google.issuer = https://accounts.google.com
    multiauth.policy.google.client_id = 42XXXX365001.apps.googleusercontent.com
    multiauth.policy.google.client_secret = UAlL-054uyh5in4b6u8jhg5o3hnj

At this point, Kinto should be properly configured and able to start.

OpenID Authentication should work as described in the :ref:`API docs <authentication-openid>`.

**Advanced settings**

.. code-block:: ini

    # User ID field name (Default: `sub`)
    multiauth.policy.google.userid_field = email
    # Authorization header prefix (Default: `Bearer`)
    multiauth.policy.google.header_type = Bearer+OIDC

    # User information cache expiration (Default: 1 day)
    # Access token verification will be cached during that amount of time.
    multiauth.policy.google.verification_ttl_seconds = 86400

    # Authentication state cache duration (Default: 1 hour)
    # Duration given to users to fill the login form on the Identity Provider.
    multiauth.policy.google.state_ttl_seconds = 3600
    # State string length (balance between collisions/security and cache size)
    multiauth.policy.google.state_length = 32

Of course, multiple OpenID providers can be enabled on the same Kinto server:

.. code-block:: ini

    multiauth.policies = google auth0
    multiauth.policy.google.use = kinto.plugins.openid.OpenIDConnectPolicy
    multiauth.policy.google.issuer = https://accounts.google.com
    # ...

    multiauth.policy.auth0.use = kinto.plugins.openid.OpenIDConnectPolicy
    multiauth.policy.auth0.issuer = https://my-service.auth0.com
    # ...


.. _settings-basicauth:

Legacy Basic Auth
:::::::::::::::::

In the first versions of Kinto, we had a built-in ``basicauth`` policy enabled by default.

Basically it generates a unique :term:`user identifier` from any username/password combination using a HMAC secret.

Even if it was convenient to get started, we decided to get rid of it because it was very confusing. But you can enable it with the follow configuration:

.. code-block:: ini

    multiauth.policies = basicauth

    kinto.userid_hmac_secret = have-you-seen-the-new-carioca
    multiauth.policy.basicauth.use = kinto.core.authentication.BasicAuthAuthenticationPolicy

.. _settings-kinto-auth-plugins:

Other Kinto plugins
:::::::::::::::::::

* `Kinto LDAP <https://github.com/Kinto/kinto-ldap>`_: Validate Basic Auth provided user login and password with an LDAP server.
* `Kinto Facebook <https://github.com/Kinto/kinto-facebook>`_:  Authentication using Facebook OAuth2 bearer tokens.
* `Kinto Portier <https://github.com/Kinto/kinto-portier>`_: Authentication using an email address.
* `Kinto Hawk <https://github.com/Kinto/kinto-hawk>`_: Authentication using... Hawk.
* `Kinto Fxa <https://github.com/Kinto/kinto-fxa>`_: Authentication using Firefox Accounts OAuth2 bearer tokens.

.. _settings-custom-auth:

Custom Authentication
:::::::::::::::::::::

Using the various `Pyramid authentication packages
<https://github.com/ITCase/awesome-pyramid#authentication>`_, it is possible
to plug in any kind of authentication.

In the following example, internal accounts, Persona, and IP Auth are all enabled:

.. code-block:: ini

    multiauth.policies = account pyramid_persona ipauth

    multiauth.policy.account.use = kinto.plugins.account.AccountsPolicy

    multiauth.policy.ipauth.use = pyramid_ipauth.IPAuthentictionPolicy
    multiauth.policy.ipauth.ipaddrs = 192.168.0.*
    multiauth.policy.ipauth.userid = LAN-user
    multiauth.policy.ipauth.principals = trusted

Permission handling and authorisation mechanisms are specified directly via
configuration. This allows for customised solutions ranging from very simple
to highly complex.

.. note::

    *Kinto* relies on :github:`pyramid multiauth <mozilla-services/pyramid_multiauth>` to initialise authentication.

.. seealso::

    Check out our tutorial about :ref:`implementing a custom authentication <tutorial-github>`


.. _configuring-notifications:

Notifications
=============

*Kinto* has a notification system, and the event listeners are configured using
the *event_handlers* setting, which takes a list of aliases.

In the example below, the Redis listener is activated and will send events
data in the ``queue`` Redis list.

.. code-block:: ini

    kinto.event_listeners = redis

    kinto.event_listeners.redis.use = kinto_redis.listeners
    kinto.event_listeners.redis.url = redis://localhost:6379/0
    kinto.event_listeners.redis.pool_size = 5
    kinto.event_listeners.redis.listname = queue

Filtering
:::::::::

It is possible to filter events by action and/or types of object. By
default actions ``create``, ``update`` and ``delete`` are notified
for every kinds of objects.

.. code-block:: ini

    kinto.event_listeners.redis.actions = create
    kinto.event_listeners.redis.resources = bucket collection

Third-party
:::::::::::

Enabling push notifications to clients consists in enabling an event listener
that will be in charge of forwarding events data to remote clients.

A Kinto plugin was made using the *Pusher* (commercial) service.
See :ref:`tutorial-notifications-websockets`.


Cross Origin requests (CORS)
============================

Kinto supports `CORS <http://www.w3.org/TR/cors/>`_ out of the box. Use the
`cors_origins` setting to change the list of accepted origins.

+--------------------+---------+--------------------------------------------------------------------------+
| Setting name       | Default | What does it do?                                                         |
+====================+=========+==========================================================================+
| kinto.cors_origins | ``*``   | This List of CORS origins to support on all endpoints. By default allow  |
|                    |         | all cross origin requests.                                               |
+--------------------+---------+--------------------------------------------------------------------------+


.. _configuring-backoff:

Backoff indicators
==================

In order to tell clients to back-off (on heavy load for instance), the
following flags can be used. Read more about this at :ref:`backoff-indicators`.

+---------------------------+----------+--------------------------------------------------------------------------+
| Setting name              | Default  | What does it do?                                                         |
+===========================+==========+==========================================================================+
| kinto.backoff             | ``None`` | The Backoff time to use. If set to `None`, no backoff flag is sent to    |
|                           |          | the clients. If set, provides the client with a number of seconds during |
|                           |          | which it should avoid doing unnecessary requests.                        |
+---------------------------+----------+--------------------------------------------------------------------------+
| kinto.backoff_percentage  | ``None`` | If specified, then send the backoff header with probability equal to the |
|                           |          | backoff_percentage. This should be a number between 0 and 100. This      |
|                           |          | setting will have no effect if the backoff is None.                      |
+---------------------------+----------+--------------------------------------------------------------------------+
| kinto.retry_after_seconds | ``30``   | The number of seconds after which the client should issue requests.      |
+---------------------------+----------+--------------------------------------------------------------------------+

.. code-block:: ini

    # kinto.backoff = 10
    kinto.retry_after_seconds = 30

Similarly, the end of service date can be specified by using these settings.

+-------------------+----------+--------------------------------------------------------------------------+
| Setting name      | Default  | What does it do?                                                         |
+===================+==========+==========================================================================+
| kinto.eos         | ``None`` | The End of Service Deprecation date. If the date specified is in the     |
|                   |          | future, an alert will be sent to clients. If it’s in the past, the       |
|                   |          | service will be declared as decomissionned. If set to `None`, no End of  |
|                   |          | Service information will be sent to the client.                          |
+-------------------+----------+--------------------------------------------------------------------------+
| kinto.eos_message | ``None`` | The End of Service message. If set to `None`, no End of Service message  |
|                   |          | will be sent to the clients.                                             |
+-------------------+----------+--------------------------------------------------------------------------+
| kinto.eos_url     | ``None`` | The End of Service information URL.                                      |
+-------------------+----------+--------------------------------------------------------------------------+

.. code-block:: ini

    kinto.eos = 2015-01-22
    kinto.eos_message = "Client is too old"
    kinto.eos_url = http://website/info-shutdown.html


Enabling or disabling endpoints
===============================

Specific resource operations can be disabled.

To do so, a setting key must be defined for the disabled resources endpoints::

    'kinto.{endpoint_type}_{resource_name}_{method}_enabled'

Where:

- **endpoint_type** is either ``collection`` (plural, e.g. ``/buckets``) or ``record`` (single, e.g. ``/buckets/abc``);
- **resource_name** is the name of the resource (e.g. ``bucket``, ``group``, ``collection``, ``record``);
- **method** is the http method (in lower case) (e.g. ``get``, ``post``, ``put``, ``patch``, ``delete``).

.. important::

    These settings are confusing because of the naming used in ``kinto.core``.
    Especially ``collection`` and ``record`` are endpoint types in ``kinto.core`` and resource names in Kinto.
    We want to solve this in #710.

For example, to disable the POST on the list of buckets and DELETE on single records, the
following setting should be declared in the ``.ini`` file:

.. code-block:: ini

    kinto.collection_bucket_post_enabled = false
    kinto.record_record_delete_enabled = false


Activating the permissions endpoint
===================================


The Permissions endpoint is used to get a list of all user accessible
objects in the server as well as their permissions. It enables
applications such as the kinto-admin to discover what the user is
allowed to do and which data can be managed.

.. code-block :: ini

    kinto.experimental_permissions_endpoint = true

Then, issue a ``GET`` request to the ``/permissions`` endpoint to get the
list of the user permissions on the server ressources.


.. _configuration-client-caching:

Client caching
==============

In addition to :ref:`per-collection caching <collection-caching>`, it is possible
to add cache control headers for every *Kinto* object.
The client (or cache server or proxy) will use them to cache the collection
records for a certain amount of time, in seconds.

The setting can be set for any kind of object (``bucket``, ``group``, ``collection``, ``record``),
and concerns GET requests (``GET /buckets``, ``GET /buckets/{}/groups``, ``GET /buckets/{}/collections``,
``GET /buckets/{}/collections/{}/records``).

.. code-block:: ini

    # kinto.bucket_cache_expires_seconds = 3600
    # kinto.group_cache_expires_seconds = 3600
    # kinto.collection_cache_expires_seconds = 3600
    kinto.record_cache_expires_seconds = 3600

It can also be specified per bucket or collections for records:

.. code-block:: ini

    kinto.blog.record_cache_expires_seconds = 30
    kinto.blog.articles.record_cache_expires_seconds = 3600

If set to ``0`` then the resource becomes uncacheable (``no-cache``).

.. note::

    In production, :ref:`Nginx can act as a cache-server <production-cache-server>`
    using those client cache control headers.


Project information
===================

+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | Default                                    | What does it do?                                                         |
+=======================================+============================================+==========================================================================+
| kinto.version_json_path               | ``./version.json``                         | Location of the file containing the information to be shown in the       |
|                                       |                                            | :ref:`version endpoint <api-utilities-version>`.                         |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.error_info_link                 | ``https://github.com/kinto/kinto/issues/`` | The HTTP link returned when uncaught errors are triggered on the server. |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.project_docs                    | ``https://kinto.readthedocs.io``           | The URL where the documentation of the Kinto instance can be found. Will |
|                                       |                                            | be returned in :ref:`the hello view <api-utilities>`.                    |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.project_name                    | ``kinto``                                  | The name of your project (powered by Kinto)                              |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.project_version                 | ``''``                                     | The version of the project. Will be returned in :ref:`the hello view     |
|                                       |                                            | <api-utilities>`. By default, this is the major version of Kinto.        |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.version_prefix_redirect_enabled | ``True``                                   | By default, all endpoints exposed by Kinto are prefixed by a             |
|                                       |                                            | :ref:`version number <api-versioning>`. If this flag is enabled, the     |
|                                       |                                            | server will redirect all requests not matching the supported version     |
|                                       |                                            | to the supported one.                                                    |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+

Example:

.. code-block:: ini

    kinto.project_docs = https://project.readthedocs.io/
    # kinto.project_version = 1.0


Application profiling
=====================

It is possible to profile the stack while its running. This is especially
useful when trying to find bottlenecks.

Update the configuration file with the following values:

.. code-block:: ini

    kinto.profiler_enabled = true
    kinto.profiler_dir = /tmp/profiling

Run some request on the server (*for example*):

::

    http GET http://localhost:8888/v1/


Render execution graphs using GraphViz:

::

    sudo apt-get install graphviz

::

    pip install gprof2dot
    gprof2dot -f pstats POST.v1.batch.000176ms.1427458675.prof | dot -Tpng -o output.png
