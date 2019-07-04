Changelog
=========

This document describes changes between each past release.

13.2.2 (2019-07-04)
-------------------

**Bug fixes**

- Fix apparence of Admin notifications (fixes #2191)


13.2.1 (2019-06-21)
-------------------

**Internal changes**

- Upgrade kinto-admin to v1.24.1


13.2.0 (2019-06-18)
-------------------

**Internal changes**

- Upgrade kinto-admin to v1.24.0


13.1.1 (2019-05-23)
-------------------

**Bug fixes**

- Fix cache heartbeat test (fixes #2107)
- Fix support of ``sqlalchemy.pool.NullPool`` for PostgreSQL backends.
  The default ``pool_size`` of 25 is maintained on the default pool class
  (``QueuePoolWithMaxBacklog``). When using custom connection pools, please
  refer to SQLAlchemy documentation for default values.


**Internal changes**

- Remove dependency to kinto-redis in core tests


13.1.0 (2019-03-20)
-------------------

**New features**

- Expose the user_profile in the user field of the hello page. (#1989)
- Add an "account validation" option to the accounts plugin. (#1973)
- Add a ``validate`` endpoint at ``/accounts/{user id}/validate/{validation
  key}`` which can be used to validate an account when the *account
  validation* option is enabled on the accounts plugin.
- Add a ``reset-password`` endpoint at ``/accounts/(user
  id)/reset-password`` which can be used to reset a user's password when the
  *account validation* option is enabled on the accounts plugin.

**Bug fixes**

- Fixed two potential bugs relating to mutable default values.
- Fix crash on validating records with errors in arrays (#1508)
- Fix crash on deleting multiple accounts (#2009)

**Documentation**

- Fixed spelling and Filtering docs

**Internal changes**

- Use ``setup.cfg`` for package metadata (ref #1921)


API is now at version **1.22**. See `API changelog`_.


13.0.1 (2019-01-29)
-------------------

**Bug fixes**

- Loosen up the Content-Security policies in the Kinto Admin plugin to prevent Webpack inline script to be rejected (fixes #2000)


13.0.0 (2019-01-25)
-------------------

**Breaking changes**

- Update Kinto OpenID plugin to redirect with a base64 JSON encoded token. (#1988).
  *This will work with kinto-admin 1.23*

**Bug fixes**

- **security**: Fix a pagination bug in the PostgreSQL backend that could leak records between collections

**Internal changes**

- Upgrade kinto-admin to v1.23.0

12.0.2 (2019-01-25)
-------------------

**Bug fixes**

- **security**: Fix a pagination bug in the PostgreSQL backend that could leak records between collections


12.0.1 (2019-01-21)
-------------------

**Bug Fixes**

- Fix bumping of tombstones timestamps when deleting objects in PostgreSQL storage backend (fixes #1981)
- Fix ETag header in responses of DELETE on plural endpoints (ref #1981)

12.0.0 (2019-01-10)
-------------------

**Breaking changes**

- Remove Python 3.5 support and upgrade to Python 3.6. (#1886)
- Remove ``record`` from UnicityError class (#1919). This enabled us to fix #1545.
- Storage backend API has changed, notions of collection and records were replaced
  by the generic terms *resource* and *object*. Plugins that subclass the internal
  ``ShareableResource`` class may also break.
- GET requests no longer include the ``Total-Records`` header. To get a count in a collection
  you need to do a HEAD request. And the new header name is ``Total-Objects``. (#1624)
- Remove the ``UserResource`` class. And ``ShareableResource`` is now deprecated in
  favor of ``Resource``.
- Removed ``kinto.core.utils.parse_resource()`. Use ``kinto.core.utils.view_lookup_registry()`` instead (#1828)
- Remove delete-collection command (#1959)

API is now at version **1.21**. See `API changelog`_.

**New features**

- Add a ``user-data`` endpoint at ``/__user_data__/`` which can be used to delete all data
  associated with a principal. This might be helpful for pursuing GDPR
  compliance, for instance. (Fixes #442.)

**Bug Fixes**

- Like query now returns 400 when a non string value is used. (#1899)
- Record ID is validated if explicitly mentioned in the collection schema (#1942)
- The Memory permission backend implementation of ``remove_principal``
  is now less generous with what it removes (#1955).

**Documentation**

- Change PostgreSQL backend URLs to be ``postgresql://`` instead of the deprecated ``postgres://``

**Internal changes**

- Remove depreciation warning for ``mapping`` (#1904)
- Fix depreciated warn method (#1903)
- Use f-string instead of % or format operators. (#1886)
- Ignore admin plugin node_modules folder while running black (#1902)
- Remove regexp py36 warnings. (#1907)
- Changed psycopg2 dependency for psycopg2-binary. (#1905)
- Renamed core notions (ie. record and collection) (#710)
- JSON Schema validation is optimized by keeping instances of validator cached. (#1807)

11.2.1 (2018-12-09)
-------------------

- Still supports jsonschema 2.6 before 3.0 is released as a production release. (#1923)


11.2.0 (2018-11-29)
-------------------

**New features**

- Return a ``500 Internal Error`` on ``__version__`` instead of 404 if the version file
  cannot be found (fixes #1841)

**Bug fixes**

- Fix the ``http_api_version`` exposed in the ``/v1/`` endpoint. The
  version ``1.20`` was getting parsed as a number ``1.2``.
- Fix ``record:create`` not taken into account from settings. (fixes #1813)

**Internal changes**

- Build the admin on the CI. (#1857)
- Migrate JSON Hyper-Schema to Draft-07 (#1808)

**Documentation**

- Add documentation on troubleshooting Auth0 multiauth issue. (#1889)


11.1.0 (2018-10-25)
-------------------

**New features**

- Add ability to configure the ``project_name`` in settings, shown in the `root URL <https://kinto.readthedocs.io/en/stable/api/1.x/utilities.html#get>`_ (fixes #1809)
- Use ``.`` as bucket/collection separator in cache control settings (fixes #1815)

**Bug fixes**

- Fix missing favicon and inline images in kinto-admin plugin

**Internal changes**

- Use mock from the standard library.
- Blackify the whole code base (#1799, huge thanks to @Cnidarias for this!)
- Upgrade kinto-admin to v1.22


11.0.0 (2018-10-09)
-------------------

**Breaking changes**

- The ``basicauth`` policy is not used by default anymore (#1736)

If your application relies on this specific behaviour, you now have to add explicitly settings:

.. code-block:: ini

    multiauth.policies = basicauth

But **it is recommended** to use other authentication policies like the *OpenID Connect* or the *accounts* plugin instead.

.. code-block:: ini

    # Enable plugin.
    kinto.includes = kinto.plugins.accounts

    # Enable authenticated policy.
    multiauth.policies = account
    multiauth.policy.account.use = kinto.plugins.accounts.AccountsPolicy

    # Allow anyone to create their own account.
    kinto.account_create_principals = system.Everyone

You will find more details the `authentication settings section of the documentation <https://kinto.readthedocs.io/en/stable/configuration/settings.html#authentication>`_

**Bug fixes**

- Fix crash when querystring filter contains NUL (0x00) character (fixes #1704)
- Many bugs were fixed in the Kinto Admin UI (see `v1.21.0 <https://github.com/Kinto/kinto-admin/releases/tag/v1.21.0>`_)

**Documentation**

- Huge refactor of documentation about authentication (#1736)

**Internal changes**

- Upgrade kinto-admin to v1.21.0
- Deprecate assertEquals and use assertEqual (fixes #1780)
- Set schema to an instance instead of class (fixes #1781)
- Fix DeprecationWarning for unrecognized backslash escapes (#1758)


10.1.2 (2018-10-03)
-------------------

**Bug fixes**

- Fix OpenID login in Kinto-Admin (Kinto/kinto-admin#641)

**Internal changes**

- Upgrade kinto-admin to v1.20.2


10.1.1 (2018-09-20)
-------------------

**Bug fixes**

- Fix for adding extra OpenId providers (fixes #1509)
- Change the meaning of ``event.payload["timestamp"]``. Previously it
  was ``@reify``\ 'd, which meant that it was calculated from before
  whatever thing triggered the event. Now we use a "fresh"
  timestamp. (Fixes #1469.)


10.1.0 (2018-09-17)
-------------------

**Bug fixes**

- Deleting a collection doesn't delete access_control_entrries for its children (fixes #1647)

**New features**

- The registry now has a "command" attribute during one-off commands
  such as ``kinto migrate``. This can be useful for plugins that want
  to behave differently during a migration, for instance. (#1762)


10.0.0 (2018-08-16)
-------------------

**Breaking changes**

- ``kinto.core.events.get_resource_events`` now returns a generator
  rather than a list.

**New features**

- Include Python 3.7 support.
- ``kinto.core.events.notify_resource_event`` now supports
  ``resource_name`` and ``resource_data``. These are useful when
  emitting events from one view "as though" they came from another
  view.
- Resource events can now trigger other resource events, which are
  handled correctly. This might be handy if one resource wants to
  simulate events on another "virtual" resource, as in ``kinto-changes``.

**Bug fixes**

- Raise a configuration error if the ``kinto.plugin.accounts`` is included without being enabled in policies.
  Without this *kinto-admin* would present a confusing login experience (fixes #1734).

**Internal changes**

- Upgrade kinto-admin to v1.20.0


9.2.3 (2018-07-05)
------------------

**Internal changes**

- Upgrade to kinto-admin v1.19.2


9.2.2 (2018-06-28)
------------------

**Internal changes**

- Upgrade to kinto-admin v1.19.1


9.2.1 (2018-06-26)
------------------

**Bug fixes**

- Fixed bug where unresolved JSON pointers would crash server (fixes #1685)

**Internal changes**

- Update the Dockerfile with the new kinto --cache-backend option. (#1686)
- Upgrade to kinto-admin v1.19.0


9.2.0 (2018-06-07)
------------------

**API**

- JSON schemas can now be defined in the bucket metadata and will apply to every
  underlying collection, group or record (fixes #1555)

API is now at version **1.20**. See `API changelog`_.

**New features**

- Kinto Admin plugin now supports OpenID Connect
- Limit network requests to current domain in Kinto Admin using `Content-Security Policies <https://hacks.mozilla.org/2016/02/implementing-content-security-policy/>`_
- Prompt for cache backend type in ``kinto init`` (#1653)
- kinto.core.utils now has new features ``route_path_registry`` and
  ``instance_uri_registry``, suitable for use when you don't
  necessarily have a ``request`` object around. The existing functions
  will remain in place.
- openid plugin will carry ``prompt=none`` querystring parameter if appended
  to authorize endpoint.

**Internal changes**

- Upgrade to kinto-admin v1.18.0


9.1.2 (2018-05-31)
------------------

**Bug fixes**

- OpenID plugin used the same cache key for every access-token (fixes #1660)


9.1.1 (2018-05-23)
------------------

**Internal changes**

- Correct spelling of GitHub.
- Upgrade to kinto-admin v1.17.2


9.1.0 (2018-05-21)
------------------

**API**

- Batch endpoint now checks for and aborts any parent request if subrequest encounters 409 constraint violation (fixes #1569)

**Bug fixes**

- Fix a bug where you could not reach the last records via Next-Header when deleting with pagination (fixes #1170)
- Slight optimizations on the ``get_all`` query in the Postgres
  storage backend which should make it faster for result sets that
  have a lot of records (#1622). This is the first change meant to
  address #1507, though more can still be done.
- Fix a bug where the batch route accepted all content-types (fixes #1529)

**Internal changes**

- Upgrage to kinto-admin v1.17.1


9.0.0 (2018-04-25)
------------------

**API**

- Introduce ``contains`` and ``contains_any`` filter operators (fixes #343).

API is now at version **1.19**. See `API changelog`_.

**Breaking changes**

- The storage class now exposes ``bump_timestamp()`` and ``bump_and_store_timestamp()`` methods
  so that memory based storage backends can use them. (#1596)

**Internal changes**

- Authentication policies can now hard code and override the name specified in settings

**Documentation**

- Version number is taken from package in order to ease release process (#1594)
- Copyright year is now dynamic (#1595)

**Internal changes**

- Upgrade the kinto-admin UI to `1.17.0 <https://github.com/Kinto/kinto-admin/releases/tag/v1.17.0>`_


8.3.0 (2018-04-06)
------------------

**Security fix**

- Validate the account user password even when the session is cached (fixes #1583).
  Since Kinto 8.2.0 the account plugin had a security flaw where the password wasn't verified during the session duration.

**New features**

- Add bucket and account creation permissions in the permissions endpoint (fixes #1510)

**Bug fixes**

- Reduce the OpenID state string length to fit in the PostgreSQL cache backend (fixes #1566)

**Documentation**

- Improve OpenID settings and API documentation

**Internal Changes**

- Now fully rely on Pyup.io (or contributors) to update the versions in the `requirements.txt` file (fixes #1512)
- Move from importing pip to running it in a subprocess (see https://github.com/pypa/pip/issues/5081).
- Remove useless print when using the OpenID policy (ref #1509)
- Try to recover from the race condition where two requests can delete the same record. (Fix #1557; refs #1407.)
- Fix a bug in the memory backend where paginating past the end of a list would restart pagination. (Refs #1584.)


8.2.2 (2018-03-28)
------------------

**Internal changes**

- Fix kinto-admin dependency error in 8.2.1 to actually really upgrade it to `1.15.1 <https://github.com/Kinto/kinto-admin/releases/tag/v1.15.1>`_


8.2.1 (2018-03-28)
------------------

**Internal changes**

- Upgraded the kinto-admin to version `1.15.1 <https://github.com/Kinto/kinto-admin/releases/tag/v1.15.1>`_
- Upgraded newrelic to `2.106.1.88 <https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes/python-agent-2106188>`_


8.2.0 (2018-03-01)
------------------

**New features**

- Add Openid connect support (#939, #1425). See `demo <https://github.com/leplatrem/kinto-oidc-demo>`_
- Account plugin now caches authentication verification (#1413)

**Bug fixes**

- Fix missing principals from user info in root URL when default bucket plugin is enabled (fixes #1495)
- Fix crash in Postgresql when the value of url param is empty (fixes #1305)

**Internal Changes**

- Upgraded the kinto-admin to version `1.15.0 <https://github.com/Kinto/kinto-admin/releases/tag/v1.15.0>`_


8.1.5 (2018-02-09)
------------------

**Bug fixes**

- Restore "look before you leap" behavior in the Postgres storage
  backend create() method to check whether a record exists before
  running the INSERT query (#1487). This check is "optimistic" in the sense
  that we can still fail to INSERT after the check succeeded, but it
  can reduce write load in configurations where there are a lot of
  create()s (i.e. when using the default_bucket plugin).


8.1.4 (2018-01-31)
------------------

**Bug fixes**

- Allow inherited resources to set a custom model instance before instantiating (fixes #1472)
- Fix collection timestamp retrieval when the stack is configured as readonly (fixes #1474)


8.1.3 (2018-01-26)
------------------

**Bug fixes**

- Optimize the PostgreSQL permission backend's
  ``delete_object_permissions`` function in the case where we are only
  matching one object_id (or object_id prefix).


8.1.2 (2018-01-24)
------------------

**Bug fixes**

- Flushing a server no longer breaks migration of the storage backend
  (#1460). If you have ever flushed a server in the past, migration
  may be broken. This version of Kinto tries to guess what version of
  the schema you're running, but may guess wrong. See
  https://github.com/Kinto/kinto/wiki/Schema-versions for some
  additional information.

**Internal changes**

- We now allow migration of the permission backend's schema.

**Operational concerns**

- *The schema for the Postgres permission backend has changed.* This
  changes another ID column to use the "C" collation, which should
  speed up the `delete_object_permissions` query when deleting a
  bucket.


8.1.1 (2018-01-18)
------------------

**Operational concerns**

- *The schema for the Postgres storage backend has changed.* This
  changes some more ID columns to use the "C" collation, which fixes a
  bug where the ``bump_timestamps`` trigger was very slow.


8.1.0 (2018-01-09)
------------------

**Internal changes**

- Update the Docker compose configuration to use memcache for the cache backend (#1405)
- Refactor the way postgresql.storage.create_from_settings ignores settings (#1410)

**Operational concerns**

- *The schema for the Postgres storage backend has changed.* This
  changes some ID columns to use the "C" collation, which will make
  ``delete_all`` queries faster. (See
  e.g. https://www.postgresql.org/docs/9.6/static/indexes-opclass.html,
  which says "If you do use the C locale, you do not need the
  xxx_pattern_ops operator classes, because an index with the default
  operator class is usable for pattern-matching queries in the C
  locale.") This may change the default sort order and grouping of
  record IDs.

**New features**

- New setting ``kinto.backoff_percentage`` to only set the backoff header a portion of the time.
- ``make tdd`` allows development in a TDD style by rerunning tests every time a file is changed.

**Bug fixes**

- Optimize the Postgres collection_timestamp method by one query. It
  now only makes two queries instead of three.
- Update other dependencies: newrelic to 2.98.0.81 (#1409), setuptools
  to 38.4.0 (#1411, #1429, #1438, #1440), pytest to 3.3.2 (#1412,
  #1437), raven to 6.4.0 (#1421), werkzeug to 0.14.1 (#1418, #1434),
  python-memcached to 1.59 (#1423), zest.releaser to 6.13.3 (#1427),
  bravado_core to 4.11.2 (#1426, #1441), statsd to 3.2.2 (#1422),
  jsonpatch to 1.21 (#1432), sqlalchemy to 1.2.0 (#1430), sphinx to
  1.6.6 (#1442).

8.0.0 (2017-11-29)
------------------

**Breaking changes**

- Storage backends no longer support the ``ignore_conflict``
  argument (#1401). Instead of using this argument, consider catching the
  ``UnicityError`` and handling it. ``ignore_conflict`` was only ever
  used in one place, in the ``default_bucket`` plugin, and was
  eventually backed out in favor of catching and handling a
  ``UnicityError``.

**Bug fixes**

- Fix a TOCTOU bug in the Postgres storage backend where a transaction
  doing a `create()` would fail because a row had been inserted after
  the transaction had checked for it (#1376).


7.6.2 (2017-11-28)
------------------

**Operational concerns**

- *The schema for the Postgres ``storage`` backend has changed.* This
  lets us prevent a race condition where deleting and creating a thing
  at the same time can leave it in an inconsistent state (#1386). You
  will have to run the ``kinto migrate`` command in order to migrate
  the schema.

**Bug fixes**

- Document how to create an account using the ``POST /accounts`` endpoint (#1385).

**Internal changes**

- Update dependency on pytest to move to 3.3.0 (#1403).
- Update other dependencies: setuptools to 38.2.1 (#1380, #1381,
  #1392, #1395), jsonpatch to 1.20 (#1393), zest.releaser to 6.13.2
  (#1397), paste-deploy to 0.4.2 (#1384), webob to 1.7.4 (#1383),
  simplejson to 3.13.2 (#1389, #1390).
- Undo workaround for broken kinto-http.js in the kinto-admin plugin
  (#1382).

7.6.1 (2017-11-17)
------------------

**Bug fixes**

- Fix kinto-admin loading.


7.6.0 (2017-11-16)
------------------

**Protocol**

- When a record is pushed with an older timestamp, the collection
  timestamps is not bumped anymore. (#1361)

**New features**

- A new custom logging formatter is available in ``kinto.core``. It fixes the issues of
  `mozilla-cloud-services-logger <https://github.com/mozilla/mozilla-cloud-services-logger>`_.
  Consider migrating your logging settings to :

::

    [formatter_json]
    class = kinto.core.JsonLogFormatter

**Bug fixes**

- Do not log empty context values (ref #1363)
- Fixed some attributes in logging of errors (ref #1363)
- Fixed logging of method/path of batch subrequests (ref #1363)
- Fix removing permissions with Json Merge (#1322).


**Internal changes**

- Moved PostgreSQL helper function to Python code (ref #1358)


7.5.1 (2017-10-03)
------------------

**Bug fixes**

- Use the ``KINTO_INI`` env variable to findout the configuration file. (#1339)
- Fix ``create-user`` command for PostgreSQL backend (#1340)
- Make sure ``create-user`` command updates password (#1336)


7.5.0 (2017-09-27)
------------------

- Add a memcached cache backend (#1332)


7.4.1 (2017-09-01)
------------------

- Failed to publish Kinto Admin


7.4.0 (2017-08-30)
------------------

**New features**

- Add a `create-user` kinto command (#1315)

**Bug fixes**

- Fix pagination token generation on optional fields (#1253)


7.3.2 (2017-08-14)
------------------

**Bug fixes**

- The PostgreSQL cache backend now orders deletes according to keys,
  which are a well-defined order that never changes. (Fixes #1308.)

**Internal changes**

- Now all configuration options appear as commented lines on the configuration
  template (#895)
- Added task on PR template about updating the configuration template
  if a new configuration setting is added.
- Use json instead of ujson in storage in tests (#1255)
- Improve Docker container to follow Dockerflow recommendations (fixes #998)


7.3.1 (2017-07-03)
------------------

**Bug fixes**

- Fix bug in Postgres backend regarding the handling of combining
  filters and NULL values.


7.3.0 (2017-06-23)
------------------

**New features**

- Account plugin now allows account IDs to be email addresses (fixes
  #1283).

**Bug fixes**

- Make it illegal for a principal to be present in
  ``account_create_principals`` without also being in
  ``account_write_principals``. Restricting creation of accounts to
  specified users only makes sense if those users are "admins", which
  means they're in ``account_write_principals``. (Fixes #1281.)
- Fix a 500 when accounts without an ID are created (fixes #1280).
- Fix StatsD unparseable metric packets for the unique user counter (fixes #1282)

**Internal changes**

- Upgraded the kinto-admin to version 1.14.0


7.2.2 (2017-06-22)
------------------

**Bug fixes**

- Fix permissions endpoint when using account plugin (fixes #1276)


7.2.1 (2017-06-20)
------------------

**Bug fixes**

- Fix missing ``collection_count`` field in the rebuild-quotas script.
- Fix bug causing validation to always succeed if no required fields are present.

**Internal changes**

- Upgraded to Pyramid-tm 2 (fixes #1187)


7.2.0 (2017-06-15)
------------------

**API**

- Filtering with like can now contain wild chars (eg. ``?like_nobody=*you*``).
  It is thus now impossible to search for the ``*`` character with this operator.
- Handle querystring parameters as JSON encoded values
  to avoid treating number as number where they should be strings. (#1217)
- Introduce ``has_`` filter operator (fixes #344).

API is now at version **1.17**. See `API changelog`_.

**Bug fixes**

- Several changes to the handling of NULLs and how the full range of
  JSON values is compared in a storage backend (PR #1258). Combined
  with #1252, this should fix #1215, #1216, #1217 and #1257, as well as
  possibly some others.
- Fix requests output when running with make serve (fixes #1242)
- Fix pagination on permissions endpoint (fixes #1157)
- Fix pagination when max fetch storage is reached (fixes #1266)
- Fix schema validation when internal fields like ``id`` or ``last_modified`` are
  marked as required (fixes #1244)
- Restore error format for JSON schema validation errors (which was
  changed in #1245).

**Internal changes**

- Add check on account plugin to avoid conflict with default ``basicauth`` policy (fixes #1177)
- Add documentation about Kinto Admin plugin (fixes #858)


7.1.0 (2017-05-31)
------------------

**New feature**

- ``delete()`` method from cache backend now returns the deleted value (fixes #1231)
- ``kinto rebuild-quotas`` script was written that can be run to
  repair the damage caused by #1226 (fixes #1230).

**Bug fixes**

- The ``default_bucket`` plugin no longer sends spurious "created"
  events for buckets and collections that already exist. This causes
  the ``quotas`` plugin to no longer leak "quota" when used with the
  ``default_bucket`` plugin. (#1226)
- Fix removal of timestamps when parent object is deleted (fixes #1233)
- Do not allow to reuse deletion tokens (fixes #1171)
- ``accounts`` plugin: fix exception on authentication. (#1224)
- Fix crash with JSONSchema validation of unknown required properties (fixes #1243)
- Fix bug on bucket deletion where other buckets could be deleted too if their id
  started with the same id
- Fix permissions of accounts created with PUT by admin (ref #1248)
- Fix ownership of accounts created with POST by admin (fixes #1248)

**Internal changes**

- Make memory storage consistent with PostgreSQL with regard to bytes (#1237)
- Some minor cleanups about the use of kinto.readonly (#1241)


7.0.1 (2017-05-17)
------------------

**Bug fixes**

- Fix missing package.json file in package. (#1222)

**Internal changes**

- Upgraded the kinto-admin to version 1.13.3


7.0.0 (2017-05-15)
------------------

**Breaking changes**

- The flush endpoint is now a built-in plugin at ``kinto.plugins.flush`` and
  should be enabled using the ``includes`` section of the configuration file.
  ``KINTO_FLUSH_ENDPOINT_ENABLED`` environment variable is no longer supported. (#1147)
- Settings with ``cliquet.`` prefix are not supported anymore.
- Logging configuration now relies on standard Python logging module (#1150)

Before:

.. code-block:: ini

    kinto.logging_renderer = kinto.core.logs.ClassicLogRenderer

Now:

.. code-block:: ini

    [handler_console]
    ...
    formatter = color

    [formatters]
    keys = color

    [formatter_color]
    class = logging_color_formatter.ColorFormatter

- Forbid storing bytes in the cache backend. (#1143)
- ``kinto.core.api`` was renamed to ``kinto.core.openapi`` (#1145)
- Logging extra information on message must be done using the ``extra`` keyword
  (eg. ``logger.info('msg', extra={a=1})`` instead of ``logger.info('msg', a=1)``)
  (#1110, #1150)
- Cache entries must now always have a TTL. The ``ttl`` parameter of ``cache.set()``
  is now mandatory (fixes #960).
- ``get_app_settings()`` from ``kinto.core.testing.BaseWebTest`` is now a
  class method (#1144)

**Protocol**

- Groups can now be created with a simple ``PUT`` (fixes #793)
- Batch requests now raise ``400`` on unknown attributes (#1163).

Protocol is now at version **1.16**. See `API changelog`_.

**New features**

- Enforce the permission endpoint when the admin plugin is included (fixes #1059)
- Access control failures are logged with WARN level (fixes #1074)
- Added an experimental Accounts API which allow users to sign-up
  modify their password or delete their account (fixes #795)

**Bug fixes**

- Fix Memory backend sometimes show empty permissions (#1045)
- Allow to create default bucket with a PUT request and an empty body (fixes #1080)
- Fix PostgreSQL backend when excluding a list of numeric values (fixes #1093)
- Fix ``ignore_conflict`` storage backend create method parameter to
  keep the existing rather than overriding it. (#1134)
- Fix impacted records of events generated by implicit creation in default
  bucket (#1137)
- Removed Structlog binding and bottlenecks (fixes #603)
- Fixed Swagger output with subpath and regex in pyramid routes (fixes #1180)
- Fixed Postgresql errors when specifying empty values in querystring numeric filters. (fixes #1194)
- Return a 400 Bad Request instead of crashing when the querystring contains bad characters. (fixes #1195)
- Fix PostgreSQL backend from deleting records of the same name in
  other buckets and collections when deleting a bucket. (fixes #1209)
- Fix race conditions on deletions with upsert in PostgreSQL ``storage.update()`` (fixes #1202)
- Fix PostgreSQL backend race condition when replacing permissions of an object (fixes #1210)
- Fix crash when deleting multiple buckets with quotas plugin enabled (fixes #1201)

**Internal changes**

- Do not keep the whole Kinto Admin bundle in the repo (fixes #1012)
- Remove the email example from the custom code event listener tutorial (fixes #420)
- Removed useless logging info from resource (ref #603)
- Make sure prefixed userid is always first in principals
- Run functional tests on PostgreSQL
- Fix tests with Pyramid 1.9a
- Removed useless deletions in quota plugin
- Upgraded the kinto-admin to version 1.13.2


6.0.0 (2017-03-03)
------------------

**Breaking changes**

- Remove Python 2.7 support and upgrade to Python 3.5. (#1050)
- Upgraded minimal PostgreSQL support to PostgreSQL 9.5 (#1056)
- The ``--ini`` parameter is now after the subcommand name (#1095)

**Protocol**

- Fixed ``If-Match`` behavior to match the RFC 2616 specification (#1102).
- A ``409 Conflict`` error response is now returned when some backend integrity
  constraint is violated (instead of ``503``) (ref #602)

Protocol is now at version **1.15**. See `API changelog`_.

**Bug fixes**

- Prevent injections in the PostgreSQL permission backend (#1061)
- Fix crash on ``If-Match: *`` (#1064)
- Handle Integer overflow in querystring parameters. (#1076)
- Flush endpoint now returns an empty JSON object instad of an HTML page (#1098)
- Fix nested sorting key breaks pagination token. (#1116)
- Remove ``deleted`` field from ``PUT`` requests over tombstones. (#1115)
- Fix crash when preconditions are used on the permission endpoint (fixes #1066)
- Fixed resource timestamp upsert in PostgreSQL backend (#1125)
- Fix pserve argument ordering with Pyramid 1.8 (#1095)

**Internal changes**

- Update the upsert query to use an INSERT or UPDATE on CONFLICT behavior (fixes #1055)
- Remove pypy supports. (#1049)
- Permission schema children fields are now set during initialization instead of on
  deserialization (#1046).
- Request schemas (including validation and deserialization) are now isolated by method
  and endpoint type (#1047).
- Move generic API schemas (e.g TimeStamps and HeaderFields) from `kinto.core.resource.schema`
  to a sepate file on `kinto.core.schema`. (#1054)
- Upgraded the kinto-admin to version 1.10.0 (#1086, #1128)
- Upgrade to Pyramid 1.8 (#1087)
- Replace old loadtests with functional tests (#1085)
- Use `Cornice Swagger <https://github.com/Cornices/cornice.ext.swagger>`_ rather than
  merging YAML files to generate the OpenAPI spec.
- Gracefully handle ``UnicityError`` with the ``default_bucket`` plugin and
  the PostgreSQL backend using PostgreSQL 9.5+ ``ON CONFLICT`` clause. (#1122)


5.3.2 (2017-01-31)
------------------

**Bug fixes**

- Retries to set value in PostgreSQL cache backend in case of BackendError (fixes #1052)


5.3.1 (2017-01-30)
------------------

**Bug fixes**

- Retries to set value in PostgreSQL cache backend in case of IntegrityError (fixes #1035)

**Internal changes**

- Remove JSON Patch content-type from accepted types on the viewset, since it is handled
  in a separate view (#1031).
- Upgraded to Kinto-Admin 1.8.1
- Configure the Kinto Admin auth methods from the server configuration (#1042)

5.3.0 (2017-01-20)
------------------

**Bug fixes**

- Fix crash with batch endpoint when list of requests contains trailing comma (fixes #1024)

**Internal changes**

- Cache backend transactions are not bound to the request/response cycle anymore (fixes #879)
- Quick mention of PostgreSQL commands to run tests locally in contributing docs.
- Use YAML ``safe_load`` for the swagger file. (#1022)
- Request headers and querystrings are now validated using cornice schemas (#873).
- JSON Patch format is now validated using cornice (#880).
- Upgraded to Kinto-Admin 1.8.0


5.2.0 (2017-01-11)
------------------

**Protocol**

- Add an `OpenAPI specification <https://kinto.readthedocs.io/en/latest/api/1.x/openapi.html>`_
  for the HTTP API on ``/__api__`` (#997)

Protocol is now at version **1.14**. See `API changelog`_.

**New features**

- When admin is enabled, ``/v1/admin`` does not return ``404`` anymore, but now redirects to
  ``/v1/admin/`` (with trailing slash).

**Bug fixes**

- Add missing ``Total-Records`` field on ``DELETE`` header with plural endpoints (fixes #1000)

**Internal changes**

- Changed default listening address from 0.0.0.0 to 127.0.0.1 (#949, thanks @PeriGK)
- Upgrade to Kinto-Admin 1.7.0


5.1.0 (2016-12-19)
------------------

**Protocol**

- Add a ``basicauth`` capability when activated on the server. (#937)
- Add ability to delete history entries using ``DELETE`` (#958)

Protocol is now at version **1.13**. See `API changelog`_.

**Bug fixes**

- Permissions are now correctly removed from permission backend when a parent
  object is deleted (fixes #898)
- Heartbeat of storage backend does not leave tombstones (fixes #985)
- Fix ``record_id`` attribute in history entries when several records are
  modified via a batch request (fixes #942)
- Fix crash on redirection when path contains control characters (fixes #962)
- Fix crash on redirection when path contains unicode characters (#982)
- Fix performance issue when fetching shared objects from plural endpoints (fixes #965)
- Fix JSON-Merge validation (fixes #979)
- Fix crash when ``If-Match`` or ``If-None-Match`` headers contain invalid
  unicode data (fixes #983)
- Add missing ``ETag`` and ``Last-Modified`` headers on ``POST`` and ``DELETE``
  responses (#980)
- Return 404 on non-existing objects for users with read permissions (fixes #918)
- Fix pagination with DELETE on plural endpoints (fixes #987)

**New features**

- Activate ``basicauth`` in admin by default. (#943)
- Add a setting to limit the maximum number of bytes cached in the memory backend. (#610)
- Add a setting to exclude certain resources from being tracked by history (fixes #964)

**Backend changes**

- ``storage.delete_all()`` now accepts ``sorting``, ``pagination_rules`` and ``limit``
  parameters (#997)
- ``permissions.get_accessible_objects()`` does not support Regexp and now accepts
  a ``with_children`` parameter (#975)
- ``cache.set()`` now logs a warning if ``ttl`` is ``None`` (#967)

**Internal changes**

- Remove usage of assert (fixes #954)
- The ``delete_object_permissions()`` of the permission backend now supports
  URI patterns (eg. ``/bucket/id*``)
- Refactor handling of prefixed user id among request principals
- Add a warning when a cache entry is set without TTL (ref #960)
- Replaced insecure use of ``random.random()`` and ``random.choice(...)`` with
  more secure ``random.SystemRandom().random()`` and
  ``random.SystemRandom().choice(...)``. (#955)
- Removed usage of pattern matching in PostgreSQL when not necessary (ref #907, fixes #974)
- Insist about authentication in concepts documentation (ref #976)
- Upgrade to Kinto-Admin 1.6.0


5.0.0 (2016-11-18)
------------------

**Breaking changes**

- Upgraded to Cornice 2.0 (#790)

**Protocol**

- Add support for `JSON-Patch (RFC 6902) <https://tools.ietf.org/html/rfc6902>`_.
- Add support for `JSON-Merge (RFC 7396) <https://tools.ietf.org/html/rfc7396>`_.
- Added a principals list to ``hello`` view when authenticated.
- Added details attribute to 404 errors. (#818)

Protocol is now at version **1.12**. See `API changelog`_.

**New features**

- Added a new built-in plugin ``kinto.plugins.admin`` to serve the kinto admin.
- Added a new ``parse_resource`` utility to ``kinto.core.utils``

**Bug fixes**

- Fixed showing of backend type twice in StatsD backend keys (fixes #857)
- Fix crash when querystring parameter contains null string (fixes #882)
- Fix crash when redirection path contains CRLF character (fixes #887)
- Fix response status for OPTION request on version redirection (fixes #852)
- Fix crash in PostgreSQL backend when specified bound permissions is empty (fixes #906)
- Permissions endpoint now exposes the user permissions defined in settings (fixes #909)
- Fix bug when two subfields are selected in partial responses (fixes #920)
- Fix crash in permission endpoint when merging permissions from settings and from
  permissions backend (fixes #926)
- Fix crash in authorization policy when object ids contain unicode (fixes #931)

**Internal changes**

- Resource ``mapping`` attribute is now deprecated, use ``schema`` instead (#790)
- Clarify implicit permissions when allowed to create child objects (#884)
- Upgrade built-in ``admin`` plugin to Kinto Admin 1.5.0
- Do not bump timestamps in PostgreSQL storage backend when non-data columns
  are modified.
- Add some specifications for the permissions endpoint with regards to inherited
  permissions
- Add deletion of multiple groups in API docs (#928)


Thanks to all contributors, with a special big-up for @gabisurita!


4.3.1 (2016-10-06)
------------------

**Bug fixes**

- Make sure we redirect endpoints with trailing slashes with the default bucket plugin. (#848)
- Fix group association when members contains ``system.Authenticated`` (fixes #776)
- Raise an error when members contains ``system.Everyone`` or a group ID (#850)
- Fix StatsD view counter with 404 responses (#853)
- Fixes filtering on ids with numeric values. (fixes #851)


4.3.0 (2016-10-04)
------------------

**Protocol**

- Fix error response consistency with safe creations if the ``create`` permission
  is granted (fixes #792). The server now returns a ``412`` instead of a ``403`` if
  the ``If-None-Match: *`` header is provided and the ``create`` permission is granted.
- The ``permissions`` attribute is now empty in the response if the user has not the permission
  to write on the object (fixes #123)
- Filtering records now works the same on the memory and postgresql backends:
  if we're comparing to a number, the filter will now filter out records that
  don't have this field. If we're comparing to anything else, the record
  without such a field is treated as if it had '' as the value for this field.
  (fixes #815)
- Parent **attributes are now readable** if children creation is allowed. That means for example
  that collection attributes are now readable to users with ``record:create`` permission.
  Same applies to bucket attributes and ``collection:create`` and ``group:create`` (fixes #803)
- Return an empty list on the plural endpoint instead of ``403`` if the ``create``
  permission is allowed

Protocol is now at version **1.11**. See `API changelog`_.

**Bug fixes**

- Fix crash in history plugin when target had no explicit permission defined (fixes #805, #842)

**New features**

- The storage backend now allows ``parent_id`` pattern matching in ``kinto.core.storage.get_all``. (#821)
- The history and quotas plugins execution time is now monitored on StatsD (``kinto.plugins.quotas``
  and ``kinto.plugins.history``) (#832)
  ``kinto.version_json_path`` settings (fixes #830)

**Internal changes**

- Fixed a failing pypy test by changing the way it was mocking
  `transaction.manager.commit` (fixes #755)
- Moved storage/cache/permissions base tests to ``kinto.core.*.testing`` (fixes #801)
- Now fails with an explicit error when StatsD is configured but not installed.
- Remove redundant fields from data column in PostgreSQL records table (fixes #762)


4.2.0 (2016-09-15)
------------------

**Protocol**

- Support for filtering records based on a text search (#791)

Protocol is now at version **1.10**. See `API changelog`_.

**Bug fixes**

- Fix concurrent writes in the memory backend (fixes #759)
- Fix heartbeat transaction locks with PostgreSQL backends (fixes #804)
- Fix crash with PostgreSQL storage backend when filtering with integer on
  a missing field (fixes #813)

**Internal changes**

- Fix links to comparison table in docs


4.1.1 (2016-08-29)
------------------

**Bug fixes**

- Fix kinto init input function (#796)


4.1.0 (2016-08-22)
------------------

**New features**

- Show warning when ``http_scheme`` is not set to ``https`` (#706, thanks @Prashant-Surya)

**Bug fixes**

- Fix sorting/filtering history entries by ``date`` field
- On subobject filtering, return a 400 error response only if first level field
  is unknown (on resources with strict schema)


4.0.1 (2016-08-22)
------------------

**New features**

- Permissions endpoint (``GET /permissions``) can now be filtered, sorted and paginated.

**Bug fixes**

- Return 400 error response when history is filtered with unknown field
- Fix crash on permissions endpoint when history is enabled (#774)
- Fix crash on history when interacting via the bucket plural endpoint (``/buckets``) (fixes #773)

**Internal changes**

- Fix documentation of errors codes (fixes #766)
- ``kinto.id_generator`` was removed from documentation since it does not
  behave as expected (fixes #757, thanks @doplumi)
  folder and a ``kinto.core.testing`` module was introduced for tests helpers
  (fixes #605)
- In documentation, link the notion of principals to the permissions page instead
  of glossary
- Add details about ``PATCH`` behaviour (fixes #566)


4.0.0 (2016-08-17)
------------------

**Breaking changes**

- ``kinto --version`` was renamed ``kinto version``
- ``ResourceChanged`` and ``AfterResourceChanged`` events now return
  ``old`` and ``new`` records for the ``delete`` action. (#751)
- Redis backends are not part of the core anymore. (#712).
  Use ``kinto_redis.cache`` instead of ``kinto.core.cache.redis``
  Use ``kinto_redis.storage`` instead of ``kinto.core.storage.redis``
  Use ``kinto_redis.permission`` instead of ``kinto.core.permission.redis``
- Redis listener is not part of the core anymore. (#712)
  Use ``kinto.event_listeners.redis.use = kinto_redis.listeners`` instead of
  ``kinto.event_listeners.redis.use = kinto.core.listeners.redis``
- Notion of unique fields was dropped from ``kinto.core`` resources.

**Protocol**

- Added a ``/__version__`` endpoint with the version that has been deployed. (#747)
- Allow sub-object filtering on plural endpoints (e.g ``?person.name=Eliot``) (#345)
- Allow sub-object sorting on plural endpoints (e.g ``?_sort=person.name``) (#345)

Protocol is now at version **1.9**. See `API changelog`_.

**New features**

- Added a new built-in plugin ``kinto.plugins.history`` that keeps track of every action
  that occured within a bucket and serves a stream of changes that can be synced.
  See `API documentation <https://kinto.readthedocs.io/en/latest/api/1.x/history.html>`_.
- Added a new ``--dry-run`` option to command-line script ``migrate`` that will simulate
  migration operation without executing on the backend (thanks @lavish205! #685)
- Added ability to plug custom StatsD backend implementations via a new ``kinto.statsd_backend``
  setting. Useful for Datadogâ˘ integration for example (fixes #626).
- Added a ``delete-collection`` action to the ``kinto`` command. (#727)
- Added verbosity options to the ``kinto`` command. (#745)
- Added a built-in plugin that allows to define quotas per bucket or collection. (#752)

**Bug fixes**

- Fix bug where the resource events of a request targetting two groups/collection
  from different buckets would be grouped together.
- Fix crash when an invalid UTF-8 character is provided in URL
- Fix crash when provided ``last_modified`` field is not divisible (e.g. string)

**Internal changes**

- Huge rework of documentation after the merge of *Cliquet* into kinto.core (#731)
- Improve the documentation about generating docs (fixes #615)
- Switch from cliquet-pusher to kinto-pusher in Dockerfile and tutorial.
- List posssible response status on every endpoint documentation (#736)
- Remove duplicated and confusing docs about generic resources
- Replace the term ``protocol`` by ``API`` in documentation (fixes #664)
- Add load tests presets (exhaustive, read, write) in addition to the existing random. Switched integration test ``make loadtest-check-simulation`` to run the exhaustive one (fixes #258)
- Remove former Cliquet load tests (#733)
- Add a flag to to run simulation load tests on ``default`` bucket. Uses ``blog``
  bucket by default (#733)
- Add command-line documentation (#727)
- The ``--backend`` command-line option for ``kinto init`` is not accepted as first
  parameter anymore
- Improved parts of the FAQ (#744)
- Improve 404 and 403 error handling to make them customizable. (#748)
- ``kinto.core`` resources are now schemaless by default (fixes #719)


3.3.3 (2016-09-12)
------------------

- Fix heartbeat transaction locks with PostgreSQL backends (fixes #804)


3.3.2 (2016-07-21)
------------------

**Bug fixes**

- Fix Redis get_accessible_object implementation (#725)
- Fix bug where the resource events of a request targetting two groups/collection
  from different buckets would be grouped together.


3.3.1 (2016-07-19)
------------------

**Protocol**

- Add the ``permissions_endpoint`` capability when the ``kinto.experimental_permissions_endpoint`` is set. (#722)


3.3.0 (2016-07-18)
------------------

**Protocol**

- Add new *experimental* endpoint ``GET /v1/permissions`` to retrieve the list of permissions
  granted on every kind of object (#600).
  Requires setting ``kinto.experimental_permissions_endpoint`` to be set to ``true``.

Protocol is now at version **1.8**. See `API changelog`_.

**Bug fixes**

- Fix crash in authorization policy when requesting ``GET /buckets/collections`` (fixes #695)
- Fix crash with PostgreSQL storage backend when provided id in POST is an integer (#688).
  Regression introduced in 3.2.0 with #655.
- Fix crash with PostgreSQL storage backend is configured as read-only and reaching
  the records endpoint of an unknown collection (fixes #693, related #558)
- Fix events payloads for actions in the default bucket (fixes #704)
- Fix bug in object permissions with memory backend
- Make sure the tombstone is deleted when the record is created with PUT. (#715)
- Allow filtering and sorting by any attribute on buckets, collections and groups list endpoints
- Fix crash in memory backend with Python3 when filtering on unknown field

**Internal changes**

- Resource events constructors signatures were changed. The event payload is now
  built immediately when event is fired instead of during transactoin commit (#704).
- Fix crash when a resource is registered without record path.
- Changed behaviour of accessible objects in permissions backend when list of
  bound permissions is empty.
- Bump ``last_modified`` on record when provided value is equal to previous
  in storage ``update()`` method (#713)
- Add ability to delete records and purge tombstones with just the ``parent_id``
  parameter (#711)
- Buckets deletion is now a lot more efficient, since every sub-objects are
  deleted with a single operation on storage backend (#711)
- Added ``get_objects_permissions()`` method in ``permission`` backend (#714)
- Changed ``get_accessible_objects()``, ``get_authorized_principals()`` methods
  in ``permission`` backend (#714)
- Simplified and improved the code quality of ``kinto.core.authorization``,
  mainly by keeping usage of ``get_bound_permissions`` callback in one place only.


3.2.0 (2016-06-14)
------------------

**Protocol**

- Allow record IDs to be any string instead of just UUIDs (fixes #655).

Protocol is now at version **1.7**. See `API changelog`_.

**New features**

- ``kinto start`` now accepts a ``--port`` option to specify which port to listen to.
  **Important**: Because of a limitation in `Pyramid tooling <http://stackoverflow.com/a/21228232/147077>`_,
  it won't work if the port is hard-coded in your existing ``.ini`` file. Replace
  it by ``%(http_port)s`` or regenerate a new configuration file with ``kinto init``.
- Add support for ``pool_timeout`` option in Redis backend (fixes #620)
- Add new setting ``kinto.heartbeat_timeout_seconds`` to control the maximum duration
  of the heartbeat endpoint (fixes #601)
- Ability to define ID generators per object type via the settings

**Bug fixes**

- Fix loss of data attributes when permissions are replaced with ``PUT`` (fixes #601)
- Fix 400 response when posting data with ``id: "default"`` in default bucket.
- Fix 500 on heartbeat endpoint when a check does not follow the specs and raises instead of
  returning false.

**Internal changes**

- Renamed some permission backend methods for consistency with other classes (fixes #608)
- Removed some deprecated code that had been in ``kinto.core`` for too long.

**Documentation**

- Mention in groups documentation that the principal of a group to be used in a permissions
  definition is the full URI (e.g. ``"write": ["/buckets/blog/groups/authors"]``)
- Fix typo in GitHub tutorial (thanks @SwhGo_oN, #673)
- New Kinto logo (thanks @AymericFaivre, #676)
- Add a slack badge to the README (#675)
- Add new questions on FAQ (thanks @enguerran, #678)
- Fix links to examples (thanks @maxdow, #680)


3.1.0 (2016-05-24)
------------------

**Protocol**

- Added the ``GET /contribute.json`` endpoint for open-source information (fixes #607)

Protocol is now at version **1.6**. See `API changelog`_.


**Bug fixes**

- Fix internal storage filtering when an empty list of values is provided.
- Authenticated users are now allowed to obtain an empty list of buckets on
  ``GET /buckets`` even if no bucket is readable (#454)
- Fix enabling flush enpoint with ``KINTO_FLUSH_ENDPOINT_ENABLED`` environment variable (fixes #588)
- Fix reading settings for events listeners from environment variables (fixes #515)
- Fix principal added to ``write`` permission when a publicly writable object
  is created/edited (fixes #645)
- Prevent client to cache and validate authenticated requests (fixes #635)
- Fix bug that prevented startup if old Cliquet configuration values
  were still around (#633)

**Documentation**

- Improved documentation about running in production with uWSGI (#543, #545)


3.0.1 (2016-05-20)
------------------

**Bug fixes**

- Fix crash when a cache expires setting is set for a specific bucket or collection. (#597)
- Mark old cliquet backend settings as deprecated (but continue to support them). (#596)


3.0.0 (2016-05-18)
------------------

- Major version update. Merged cliquet into kinto.core. This is
  intended to simplify the experience of people who are new to Kinto.
  Addresses #687.
- Removed ``initialize_cliquet()``, which has been deprecated for a while.
- Removed ``cliquet_protocol_version``. Kinto already defines
  incompatible API variations as part of its URL format (e.g. ``/v0``,
  ``/v1``). Services based on kinto.core are free to use
  ``http_api_version`` to indicate any additional changes to their
  APIs.
- Simplify settings code. Previously, ``public_settings`` could be
  prefixed with a project name, which would be reflected in the output
  of the ``hello`` view. However, this was never part of the API
  specification, and was meant to be solely a backwards-compatibility
  hack for first-generation Kinto clients. Kinto public settings
  should always be exposed unprefixed. Applications developed against
  kinto.core can continue using these names even after they transition
  clients to the new implementation of their service.

**Bug fixes**

- Add an explicit message when the server is configured as read-only and the
  collection timestamp fails to be saved (ref Kinto/kinto#558)
- Prevent the browser to cache server responses between two sessions. (#593)
- Redirects version prefix to hello page when trailing_slash_redirect is enabled. (#700)
- Fix crash when setting empty permission list with PostgreSQL permission backend (fixes Kinto/kinto#575)
- Fix crash when type of values in querystring for exclude/include is wrong (fixes Kinto/kinto#587)
- Fix crash when providing duplicated principals in permissions with PostgreSQL permission backend (fixes #702)
- Add ``app.wsgi`` to the manifest file. This helps address #543.


2.1.1 (2016-04-29)
------------------

**Bug fixes**

- Fix crash in JSON schema validation when additional properties are provided (fixes #548)
- Strip internal fields before validating JSON schema (fixes #549)
- Fix migration of triggers in PostgreSQL storage backend when upgrading from Kinto<2.0.
  Run the ``migrate`` command will basically re-create them (fixes #559)

**Documentation**

- Fix typo in RHEL installation instructions (#552, thanks @enkidulan!)
- Link to english version of kinto presentation article (#553, thanks @glasserc!)
- Document basics about PostgreSQL privileges (#547)
- Change links from readthedocs.org to readthedocs.io (#557)
- Fix Parse server license in docs (#571, thanks @revolunet!)


2.1.0 (2016-04-19)
------------------

**Bug fixes**

- Relax content-type validation when no body is posted (fixes #507)
- Fix creation events not sent for implicit creation of objects in the ``default``
  bucket (fixes #529)
- Fix the Dockerfile pip install (#522)
- Fix concurrency control request headers to recreate deleted objects (#512)

**New features**

- Allow groups to store arbitrary properties. (#469)
- A ``cache_prefix`` setting was added for cache backends. (mozilla-services/cliquet#680)

**Documentation**

- Put the cloud provider links in a comparison table (#514)
- Fix the module name of Redis event listener (thanks @happy-tanuki, #516)
- Add Makefile Documentation (thanks @ayusharma, #483)
- Document how to run Docker with custom config file (#525)
- Fix API version title (#523)
- Add a 'upgrade pip' command in the getting-started docs (#531)
- Document how to configure the postgresql backend (#533)
- Document how to upgrade Kinto (#537, #538)

Protocol is now in version **1.5**. See `API changelog`_.


2.0.0 (2016-03-08)
------------------

**Protocol**

- Allow buckets to store arbitrary properties. (#239, #462)
- Delete every (writable) buckets using ``DELETE /v1/buckets``
- Delete every (writable) collections using ``DELETE /v1/buckets/<bucket-id>/collections``
- Clients are redirected to URLs without trailing slash only if the current URL
  does not exist (#656)
- Partial responses can now be specified for nested objects (#445)
  For example, ``/records?_fields=address.street``.
- List responses are now sorted by last_modified descending by default (#434,
  thanks @ayusharma)
- Server now returns 415 error response if client cannot accept JSON response (#461, mozilla-services/cliquet#667)
- Server now returns 415 error response if client does not send JSON request (#461, mozilla-services/cliquet#667)
- Add the ``__lbheartbeat__`` endpoint, for load balancer membership test.
- Add the ``flush_endpoint``, ``schema`` and ``default_bucket`` to the capabilities
  if enabled in settings (#270)

Protocol is now in version **1.4**. See `API changelog`_.

**Breaking changes**

- ``kinto.plugins.default_bucket`` plugin is no longer assumed. We invite users
  to check that the ``kinto.plugins.default_bucket`` is present in the
  ``includes`` setting if they expect it. (ref #495)
- ``kinto start`` must be explicitly run with ``--reload`` in order to
  restart the server when code or configuration changes (ref #490).
- Errors are not swallowed anymore during the execution of ``ResourceChanged``
  events subscribers.

  Subscribers are still executed within the transaction like before.

  Subscribers are still executed even if the transaction is eventually rolledback.
  Every subscriber execution succeeds, or none.

  Thus, subscribers of these events should only perform operations that are reversed
  on transaction rollback: most likely database storage operations.

  For irreversible operations see the new ``AfterResourceChanged`` event.

**New features**

- Event subscribers are now ran synchronously and can thus alter responses (#421)
- Resource events are now merged in batch requests. One event per resource and
  per action is emitted when a transaction is committed (mozilla-services/cliquet#634)
- Monitor time of events listeners execution (mozilla-services/cliquet#503)
- Added a new ``AfterResourceChanged`` event, that is sent only when the commit
  in database is done and successful.
  `See more details <https://cliquet.readthedocs.io/en/latest/reference/notifications.html>`_.
- Track execution time on StatsD for each authentication sub-policy (mozilla-services/cliquet#639)
- Default console log renderer now has colours (mozilla-service/cliquet#671)
- Output Kinto version with ``kinto --version`` (thanks @ayusharma)

**Bug fixes**

- Fix PostgreSQL backend timestamps when collection is empty (#433)
- ``ResourceChanged`` events are not emitted if a batch subrequest fails (mozilla-services/cliquet#634)
  There are still emitted if the whole batch transaction is eventually rolledback.
- Fix a migration of PostgreSQL schema introduced that was never executed (mozilla-services/cliquet#604)
- Fix statsd initialization on storage (mozilla-services/cliquet#637)
- Providing bad last modified values on delete now returns 400 (mozilla-services/cliquet#665)
- Providing last modified in the past for delete now follows behaviour create/update (mozilla-services/cliquet#665)
- Do not always return 412 errors when request header ``If-None-Match: *``
  is sent on ``POST /collection`` (fixes #489, mozilla-service/cliquet#673)
- Fix secret in ini on Python 3 (fixes #341)
- Error when trying to create an empty directory (fixes #475)
- Text plain body should be rejected with an error (#461)

**Documentation**

- Additions in troubleshooting docs (thanks @ayusharma)
- Add uwsgi bind error to troubleshooting (fixes #447)
- Mention python plugin for Uwsgi (#448)
- Add how to troubleshoot psql encoding problems. (#453)
- Add mini checklist for CDN deployment (#450)
- Replace subjective ligthweight by minimalist (fixes #417)
- Improve synchronisation docs (#451)
- Add the requirements in the Readme (#465)
- Add docs about architecture (fixes #430)
- Add a 'why' paragraph to the docs (Kinto value proposition) (#482)
- Update docs: how to choose the backend (#485, thanks @Enguerran)
- Add a custom id generator tutorial (#464)

**Internal changes**

- Changed default duration between retries on error (``Retry-After`` header)
  from 30 to 3 seconds.
- Speed-up startup (ref #490)
- Optimized (and cleaned) usage of (un)authenticated_userid (#424, mozilla-services/cliquet#641)
- Fixed usage of virtualenv in Makefile (#443)
- Add a badge for the irc channel (#459)
- Change phrasing for backend selection (#470)
- Add a CONTRIBUTING file (#471, thanks @magopian)
- Add a contribute.json file (#478, #480, thanks @magopian)


1.11.2 (2016-02-03)
------------------=

**Bug fixes**

- Expose the ETag header in 304 responses for default bucket (ref mozilla-services/cliquet#631)

**Documentation**

- Add Scalingo *one-click deploy* button (#418, thanks @yannski)
- Improve introduction of notifications tutorial (#419, thanks @tarekziade)
- Fix typos (thanks @magopian)


1.11.1 (2016-02-01)
------------------=

**Bug fixes**

- Fix wheels for Python 3 that were requiring the functools32 package that is
  for Python 2 only (fixes #303).

**Documentation**

- Fix a broken hyperlink in the overview section. (#406, thanks William Hoang)
- Talk about tokens rather than user:password (#393)


1.11.0 (2016-01-28)
------------------=

**Protocol**

- Forward slashes (``/``) are not escaped anymore in JSON responses (mozilla-services/cliquet#537)
- Fields can be filtered in GET requests using ``_fields=f1,f2`` in querystring (#399)
- New collections can be created via ``POST`` requests (thanks John Giannelos)
- The API capabilities can be exposed in a ``capabilities`` attribute in the
  root URL (#628). Clients can rely on this to detect optional features on the
  server (e.g. enabled plugins)

Protocol is now version 1.3. See `API changelog`_.

**New features**

- Add a Heroku single-clic deploy button (#362)
- Install PostgreSQL libraries on ``kinto init`` (fixes #313)
- Smaller Docker container image (#375, #376, #383)
- Install major plugins in Dockerfile (fixes #317)
- The policy name used to configure authentication in settings is now used for
  the user id prefix and StatsD ``authn_type`` counters.
- Check backends configuration at startup (#228)
- Output message for config file creation (#351, thanks Aditya Basin)
- Trigger internal event on server flush (#354)

**Bug fixes**

- Fix validation of collection id in default bucket (fixes #260)
- Fix kinto init failure when the config folder already exists (#349)
- Fix Docker compose startup (fixes #325)
- Run migrate command when Docker container starts (fixes #363)
- Fix listener name logging during startup (#626)
- Do not log batch subrequests twice (#264)
- Fix hmac digest with Python 3 (#288)
- Add explicit dependency for functools32 when Kinto is installed with an old
  pip version (fixes #303)

**Documentation**

Highlights:

- Add tutorials about notifications (ref #353)
- Add tutorial how to write a plugin (#382)
- Add tutorial how to setup GitHub authentication (#390)
- Move default values to dedicated column in docs (fixes #255)
- Move run-kinto to get-started and remove platform specific installation
  instructions (#373)

Improved:

- Update features table in overview
- Update overview comparisons (#294, #324, #328)
- Update FAQ (#397, #398)
- Simplify some aspects of the settings page (#374)
- Sharding documentation (#381)

Minor:

- Added missing DELETE endoint for list of records (fixes #238)
- Mention how to restrict private URLs with NGinx (fixes #250)
- Fix link to the freenode #kinto channel in the docs (#333)
- Remove Firefox Account mention from README (fixes #326)
- Move application examples page to wiki (ref #321)
- Move PostgreSQL server docs to wiki (fixes #321)
- Change colors of logo (#359)
- Add invitation for community to point their demos/use cases (fixes #356)
- Remove duplicate glossary in docs (#372)
- Remove troubleshooting paragraph from contributing page (#385)
- Fix wrong groups name and permissions names in the documentation (#389)
- Improve formatting of code block in tutorials (#391, #396)

**Internal changes**

- Default bucket feature is now a built-in plugin (fixes #277, fixes #311, #380)
- Do not require cliquet master branch in dev (#341, #400). Now moved as tox env in TravisCI


1.10.1 (2015-12-11)
------------------=

**Bug fixes**

- Fix ``kinto init`` when containing folder does not exist (fixes #302)

**Internal changes**

- Added Hoodie in the comparison matrix (#282, thanks @Niraj8!)
- Added a get started button in documentation (#315, thanks @Niraj8!)


1.10.0 (2015-12-01)
------------------=

**Breaking changes**

- When using *cliquet-fxa*, the setting ``multiauth.policy.fxa.use`` must now
  be explicitly set to ``cliquet_fxa.authentication.FxAOAuthAuthenticationPolicy``
- Fields in the root view were renamed (mozilla-services/cliquet#600)

**Bug fixes**

- Fix redis default host in kinto init (fixes #289)
- Fix DockerFile with default configuration (fixes #296)
- Include plugins after setting up components (like authn/authz) so that plugins
  can register views with permissions checking
- Remove ``__permissions__`` from impacted records values in ``ResourceChanged``
  events (mozilla-services/cliquet#586)

**Protocol**

Changed the naming in the root URL (hello view) (mozilla-services/cliquet#600)

- Added ``http_api_version``
- Renamed ``hello`` to ``project_name``
- Renamed ``protocol_version`` to ``cliquet_protocol_version``
- Renamed ``documentation`` to ``project_docs``
- Renamed ``version`` to ``project_version``


**New features**

- New options in configuration of listeners to specify filtered actions and
  resource names (mozilla-services/cliquet#492, mozilla-services/cliquet#555)
- Add ability to be notified on read actions on a resource (disabled by
  default) (mozilla-services/cliquet#493)

**Internal changes**

- Clarified how Kinto is versionned in the documentation (#305)

1.9.0 (2015-11-18)
------------------

- Upgraded to *Cliquet* 2.11.0

**Breaking changes**

- For PostgreSQL backends, it is recommended to specify ``postgresql://``.

**Protocol**

- In the hello view:

   - Add a ``bucket`` attribute in ``user`` mapping allowing clients
     to obtain the actual id of their default bucket
   - Add the ``protocol_version`` to tell which protocol version is
     implemented by the service. (#324)

- ``_since`` and ``_before`` now accepts an integer value between quotes ``"``,
  as it would be returned in the ``ETag`` response header.
- A batch request now fails if one of the subrequests fails
  (mozilla-services/cliquet#510) (*see new feature about
  transactions*)

**New features**

- Add a Kinto command for start and migrate operation. (#129)
- Add a Kinto command to create a configuration file. (#278)
- A transaction now covers the whole request/response cycle (#194).
  If an error occurs during the request processing, every operation performed
  is rolled back. **Note:** This is only enabled with *PostgreSQL* backends. In
  other words, the rollback has no effect on backends like *Redis* or *Memory*.

- New settings for backends when using PostgreSQL: ``*_max_backlog``,
  ``*_max_overflow``, ``*_pool_recycle``, ``*_pool_timeout`` to
  control connections pool behaviour.

**Bug fixes**

- Fix 500 error response (instead of 503) when storage backend fails during
  implicit creation of objects on ``default`` bucket. (fixes #236)
- Fixed ``Dockerfile`` for PostgreSQL backends.
- Fix JSON schema crash when no field information is available.

**Internal changes**

- Optimization for retrieval of user principals (#263)
- Do not build the Docker container when using Docker Compose.
- Add Python 3.5 on TravisCI
- Add schema validation loadtest (fixes #201)
- Multiple documentation improvements.
- The PostgreSQL backends now use SQLAlchemy sessions.

See also `*Cliquet* changes <https://github.com/mozilla-services/cliquet/releases/2.11.0>`_


1.8.0 (2015-10-30)
------------------

- Upgraded to *Cliquet* 2.10.0

**Protocol breaking changes**

- Moved ``userid`` attribute to a dedicated ``user`` mapping in the hello
  view (#242).

**New features**

- Follow redirections in batch subrequests (fixes mozilla-services/cliquet#511)
- Set cache headers only when anonymous (fixes mozilla-services/cliquet#449)
- Add a ``readonly`` setting to run the service in read-only mode. (#241)
- If no client cache is set, add ``Cache-Control: no-cache`` by default,
  so that clients are forced to revalidate their cache against the server
  (ref Kinto/kinto#231)

**Bug fixes**

- Fixed 503 error message to mention backend errors in addition to unavailability.
- When recreating a record that was previously deleted, status code is now ``201``
  (ref mozilla-services/cliquet#530).
- Fix PostgreSQL error when deleting an empty collection in a protected
  resource (fixes mozilla-services/cliquet#528)
- Fix PUT not using ``create()`` method in storage backend when tombstone exists
  (fixes mozilla-services/cliquet#530)
- Delete tombstone when record is re-created (fixes mozilla-services/cliquet#518)
- Fix crash with empty body for PATCH (fixes mozilla-services/cliquet#477,
  fixes mozilla-services/cliquet#516)
- Fix english typo in 404 error message (fixes mozilla-services/cliquet#527)


1.7.0 (2015-10-28)
------------------

- Upgraded to *Cliquet* 2.9.0
- Update cliquet-fxa configuration example for cliquet-fxa 1.4.0
- Improve the documentation to get started

**New features**

- Added Pyramid events, triggered when the content of a resource has changed. (#488)
- Added ``kinto.includes`` setting allowing loading of plugins once Kinto
  is initialized (unlike ``pyramid.includes``). (#504)


**Protocol**

- Remove the broken git revision ``commit`` field in the hello page. (#495).

`Please read the full Cliquet 2.9.0 changelog for more information <https://github.com/mozilla-services/cliquet/releases/tag/2.9.0>`_

1.6.2 (2015-10-22)
------------------

**Bug fixes**

- Handle 412 details with default bucket (#226)


1.6.1 (2015-10-22)
------------------

- Upgraded to *Cliquet* 2.8.2

**Bug fixes**

- Return a JSON body for 405 response on the default bucket (#214)

**Internal changes**

- Improve documentation for new comers (#217)
- Do not force host in default configuration (#219)
- Use tox installed in virtualenv (#221)
- Skip python versions unavailable in tox (#222)


1.6.0 (2015-10-14)
------------------

- Upgraded to *Cliquet* 2.8.1

**Breaking changes**

- Settings prefixed with ``cliquet.`` are now deprecated, and should be replaced
  with non prefixed version instead.
- In the root url response, public settings are exposed without prefix too
  (e.g. ``batch_max_requests``).


1.5.1 (2015-10-07)
------------------

- Upgraded to *Cliquet* 2.7.0


1.5.0 (2015-09-23)
------------------

- Add Disqus comments to documentation (fixes #159)

**New features**

- Allow POST to create buckets (fixes #64)
- Control client cache headers from settings or collection objects (#189)

**Internal changes**

- Remove dead code (#187, ref #53)
- Add pytest-capturelog for better output on test failures (#191)
- Install cliquet middleware (*no-op if disabled*) (#193)
- Many optimizations on ``default`` bucket (#192, #197)
- Many optimizations on number of storage hits (#203)
- Fix contributing docs about tests (#198)
- Added more batched actions to loadtests (#199)


1.4.0 (2015-09-04)
------------------

**New features**

- Partial collection of records when user has no ``read`` permission on collection (fixes #76).
  Alice can now obtain a list of Bob records on which she has individual ``read`` permission!
- Collection can now specify a JSON schema and validate its records (#31).
  The feature is marked as *experimental* and should be explicitly enabled
  from settings (#181)
- Accept empty payload on buckets and collections creation (#63)
- Allow underscores in Kinto bucket and collection names (#153, fixes #77)
- Collection records can now be filtered using multiple values (``?in_status=1,2,3``) (mozilla-services/cliquet#39)
- Collection records can now be filtered excluding multiple values (``?exclude_status=1,2,3``) (mozilla-services/readinglist#68)
- Current userid is now provided when requesting the hello endpoint with an ``Authorization``
  header (mozilla-services/cliquet#319)
- UUID validation now accepts any kind of UUID, not just v4 (mozilla-services/cliquet#387)
- Querystring parameter ``_to`` on collection records was renamed to ``_before`` (*the former is now
  deprecated*) (mozilla-services/cliquet#391)
- Allow to configure info link in error responses with ``cliquet.error_info_link``
  setting (mozilla-services/cliquet#395)

**Bug fixes**

- Fix consistency in API to modify permissions with PATCH (fixes #155)
  The list of principals for each specified permission is now replaced by the one
  provided.
- Use correct HTTP Headers encoding in both Python2 and Python3 (#141)
- ETag is now returned on every verb (fixes #110)

**Internal changes**

- When deleting a collection also remove the records tombstones (#136)
- Complete revamp of the documentation (#156 #167 #168 #169 #170)
- Upgraded to *Cliquet* 2.6.0


1.3.1 (2015-07-15)
------------------

- Upgraded to *Cliquet* 2.3.1

**Bug fixes**

- Make sure the default route only catch /buckets/default and
  /buckets/default/* routes. (#131)


1.3.0 (2015-07-13)
------------------

- Upgraded to *Cliquet* 2.3.0

**Bug fixes**

- Handle CORS with the default bucket. (#126, #135)
- Add a test to make sure the tutorial works. (#118)

**Internal changes**

- List StatsD counters and timers in documentation (fixes #73)
- Update virtualenv dependencies on setup.py modification (fixes #130)


1.2.1 (2015-07-08)
------------------

- Upgraded to *Cliquet* 2.2.1

**Bug fixes**

- Improvements and fixes in the tutorial (#107)
- Querystring handling when using the personal bucket (#119)
- Default buckets ID is now a UUID with dashes (#120)
- Handle unknown permission and fix crash on /buckets (#88)
- Fix permissions handling on PATCH /resource (mozilla-services/cliquet#358)

**Internal changes**

- Test with the normal Kinto authentication policy and remove the fake one (#121)


1.2.0 (2015-07-03)
------------------

- Upgraded to *Cliquet* 2.2.+

**New features**

- Add the personal bucket ``/buckets/default``, where collections are created
  implicitly (#71)
- *Kinto* now uses the memory backend by default, which simplifies its usage
  for development (#86, #95)
- Add public settings in hello view (mozilla-services/cliquet#318)

**Bug fixes**

- Fix Docker compose file settings (#100)
- Fix version redirection behaviour for unsupported versions (mozilla-services/cliquet#341)
- Fix overriding backend settings in .ini (mozilla-services/cliquet#343)

**Internal changes**

- Documentation improvements (#75)
- Added tutorial (#79)
- Remove hard dependency on *PostgreSQL* (#100)
- Add pytest-cache (#98)
- Add Pypy test on Travis (#99)
- Update dependencies on ``make install`` (#97)
- Fix URL of readthedocs.io (#90)


1.1.0 (2015-06-29)
------------------

**New features**

- Polish default kinto configuration and default to memory backend. (#81)
- Add the kinto group finder (#78)
- Flush endpoint now returns 404 is disabled (instead of 405) (#82)


**Bug fixes**

- ETag not updated on collection update (#80)


**Internal changes**

- Use py.test to run tests instead of nose (#85)


1.0.0 (2015-06-17)
------------------

**New features**

- Added notion of buckets, user groups and collections (#48, #58)
- Buckets, collections and records can now have permissions (#59)

**Breaking changes**

- Updated *Cliquet* to 2.0, which introduces a lot of breaking changes
  (`see changelog <https://github.com/mozilla-services/cliquet/releases/2.0.0>`_)
- Firefox Accounts is not a dependency anymore and should be installed and
  included explictly using the python package ``cliquet-fxa``
  (`see documentation <https://github.com/mozilla-services/cliquet-fxa/>`_)
- API is now served under ``/v1``
- Collections are now managed by bucket, and not by user anymore (#44)

.. note::

    A list of records cannot be manipulated until its parents objects (bucket and
    collection) are created.

Settings

- ``cliquet.permission_backend`` and ``cliquet.permission_url`` are now configured
  to use PostgreSQL instead of *Redis* (see default ``config/kinto.ini``)
- ``cliquet.basic_auth_enabled`` is now deprecated (`see *Cliquet*
  docs to enable authentication backends
  <https://cliquet.readthedocs.io/en/latest/reference/configuration.html#basic-auth>`_)


**Internal changes**

- Added documentation about deployment and data durability (#50)
- Added load tests (#30)
- Several improvements in documentation (#51)


0.2.2 (2015-06-04)
------------------

- Upgraded to *cliquet* 1.8.+

**Breaking changes**

- PostgreSQL database initialization process is not run automatically in
  production. Add this command to deployment procedure:

::

    cliquet --ini config/kinto.ini migrate

**Internal changes**

- Improved documentation (#29)
- Require 100% coverage during tests (#27)
- Basic Auth is now enabled by default in example config


0.2.1 (2015-03-25)
------------------

- Upgraded to *cliquet* 1.4.1

**Bug fixes**

- Rely on Pyramid API to build pagination Next-Url (#147)


0.2 (2015-03-24)
----------------

- Upgraded to *cliquet* 1.4

**Bug fixes**

- Fix behaviour of CloudStorage with backslashes in querystring (mozilla-services/cliquet#142)
- Force PostgreSQl session timezone to UTC (mozilla-services/cliquet#122)
- Fix basic auth ofuscation and prefix (mozilla-services/cliquet#128)
- Make sure the `paginate_by` setting overrides the passed `limit`
  argument (mozilla-services/cliquet#129)
- Fix crash of classic logger with unicode (mozilla-services/cliquet#142)
- Fix crash of CloudStorage backend when remote returns 500 (mozilla-services/cliquet#142)
- Fix python3.4 segmentation fault (mozilla-services/cliquet#142)
- Add missing port in Next-Page header (mozilla-services/cliquet#147)


0.1 (2015-03-20)
----------------

**Initial version**

- Schemaless storage of records
- Firefox Account authentication
- Kinto as a storage backend for *cliquet* applications


.. _API changelog: https://kinto.readthedocs.io/en/latest/api/
