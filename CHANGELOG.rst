Changelog
=========

This document describes changes between each past release.

2.0.0 (2015-06-16)
------------------

**New features**

- Authentication and authorization policies, as well as group finder function
  can now be specified via configuration (fixes #40, #265)
- Resources can now be protected by fine-grained permissions (#288 via #291, #302)

Minor

- Preserve provided ``id`` field of records using POST on collection (#293 via #294)
- Logging value for authentication type is now available for any kind of
  authentication policy.
- Any resource endpoint can now be disabled from settings (#46 via #268)

**Bug fixes**

- Do not limit cache values to string (#279)
- When PUT creates the record, the HTTP status code is now 201 (#298, #300)
- Add safety check in ``utils.current_service()`` (#316)

**Breaking changes**

- ``cliquet.storage.postgresql`` now requires PostgreSQL version 9.4, since it
  now relies on *JSONB*. Data will be migrated automatically using the ``migrate``
  command.
- the ``@crud`` decorator was replaced by ``@register()`` (fixes #12, #268)
- Firefox Accounts code was removed and published as external package *cliquet-fxa*
- The *Cloud storage* storage backend was removed out of *Cliquet* and should
  be revamped in *Kinto* repository (mozilla-services/kinto#45)

API

- Resource endpoints now expect payloads to have a ``data`` attribute (#254, #287)
- Resource endpoints switched from ``If-Modified-Since`` and ``If-Unmodified-Since``
  to ``Etags`` (fixes #251 via #275), thanks @michielbdejong!

Minor

- ``existing`` attribute of conflict errors responses was moved inside a generic
  ``details`` attribute that is also used to list validation errors.
- Setting ``cliquet.basic_auth_enabled`` is now deprecated.
  Use `pyramid_multiauth <https://github.com/mozilla-services/pyramid_multiauth>`_
  configuration instead to specify authentication policies.
- Logging value for authentication type is now ``authn_type`` (with ``FxAOAuth``
  or ``BasicAuth`` as default values).

**Internal changes**

- Cliquet resource code was split into ``Collection`` and ``Resource`` (fixes #243, #282)
- Cleaner separation of concern between ``Resource`` and the new notion of ``ViewSet`` (#268)
- Quickstart documentation improvement (#271, #312) thanks @N1k0 and @brouberol!
- API versioning documentation improvements (#313)
- Contribution documentation improvement (#306)


1.8.0 (2015-05-13)
------------------

**Breaking changes**

- Switch PostgreSQL storage to JSONB: requires 9.4+ (#104)
- Resource name is not a Python property anymore (ref #243)
- Return existing record instead of raising 409 on POST (fixes #75)
- ``cliquet.storage.postgresql`` now requires version PostgreSQL 9.4, since it
  now relies on *JSONB*. Data will be migrated automatically using the ``migrate``
  command.
- Conflict errors responses ``existing`` attribute was moved inside a generic
  ``details`` attribute that is also used to list validation errors.
- In heartbeat end-point response, ``database`` attribute was renamed to ``storage``

**New features**

- Storage records ids are now managed in python (fixes #71, #208)
- Add setting to disable version redirection (#107, thanks @hiromipaw)
- Add response behaviour headers for PATCH on record (#234)
- Provide details in error responses (#233)
- Expose new function ``cliquet.load_default_settings()`` to ease reading of
  settings from defaults and environment (#264)
- Heartbeat callback functions can now be registered during startup (#261)

**Bug fixes**

- Fix migration behaviour when metadata table is flushed (#221)
- Fix backoff header presence if disabled in settings (#238)

**Internal changes**

- Require 100% of coverage for tests to pass
- Add original error message to storage backend error
- A lots of improvements in documentation (#212, #225, #228, #229, #237, #246,
  #247, #248, #256, #266, thanks Michiel De Jong)
- Migrate *Kinto* storage schema on startup (#218)
- Fields ``id`` and ``last_modified`` are not part of resource schema anymore
  (#217, mozilla-services/readinlist#170)
- Got rid of redundant indices in storage schema (#208, ref #138)
- Disable Cornice schema request binding (#172)
- Do not hide FxA errors (fixes mozilla-services/readinglist#70)
- Move initialization functions to dedicated module (ref #137)
- Got rid of request custom attributes for storage and cache (#245)


1.7.0 (2015-04-10)
------------------

**Breaking changes**

- A **command must be ran during deployment** for database schema migration:

    $ cliquet --ini production.ini migrate

- Sentry custom code was removed. Sentry logging is now managed through the
  logging configuration, as explained `in docs <http://raven.readthedocs.org/en/latest/integrations/pyramid.html#logger-setup>`_.

**New features**

- Add PostgreSQL schema migration system (#139)
- Add cache and oauth in heartbeat view (#184)
- Add monitoring features using NewRelic (#189)
- Add profiling features using Werkzeug (#196)
- Add ability to override default settings in initialization (#136)
- Add more statsd counter for views and authentication (#200)
- Add in-memory cache class (#127)

**Bug fixes**

- Fix crash in DELETE on collection with PostgreSQL backend
- Fix Heka logging format of objects (#199)
- Fix performance of record insertion using ordered index (#138)
- Fix 405 errors not JSON formatted (#88)
- Fix basic auth prompt when disabled (#182)

**Internal changes**

- Improve development setup documentation (thanks @hiromipaw)
- Deprecated ``cliquet.initialize_cliquet``, renamed to ``cliquet.initialize``.
- Code coverage of tests is now 100%
- Skip unstable tests on TravisCI, caused by ``fsync = off`` in their PostgreSQL.
- Perform random creation and deletion in heartbeat view (#202)


1.6.0 (2015-03-30)
------------------

**New features**

- Split schema initialization from application startup, using a command-line
  tool.

::

    cliquet --ini production.ini init


**Bug fixes**

- Fix connection pool no being shared between cache and storage (#176)
- Default connection pool size to 10 (instead of 50) (#176)
- Warn if PostgreSQL session has not UTC timezone (#177)

**Internal changes**

- Deprecated ``cliquet.storage_pool_maxconn`` and ``cliquet.cache_pool_maxconn``
  settings (renamed to ``cliquet.storage_pool_size`` and ``cliquet.cache_pool_size``)


1.5.0 (2015-03-27)
------------------

**New features**

- Mesure calls on the authentication policy (#167)

**Breaking changes**

- Prefix statsd metrics with the value of `cliquet.statsd_prefix` or
  `cliquet.project_name` (#162)
- `http_scheme` setting has been replaced by `cliquet.http_scheme` and
  `cliquet.http_host` was introduced ((#151, #166)
- URL in the hello view now has version prefix (#165)

**Bug fixes**

- Fix Next-Page url if service has key in url (#158)
- Fix some PostgreSQL connection bottlenecks (#170)

**Internal changes**

- Update of PyFxA to get it working with gevent monkey patching (#168)
- Reload kinto on changes (#158)


1.4.1 (2015-03-25)
------------------

**Bug fixes**

- Rely on Pyramid API to build pagination Next-Url (#147)


1.4.0 (2015-03-24)
------------------

**Breaking changes**

- Make monitoring dependencies optional (#121)

**Bug fixes**

- Force PostgreSQl session timezone to UTC (#122)
- Fix basic auth ofuscation and prefix (#128)
- Make sure the `paginate_by` setting overrides the passed `limit`
  argument (#129)
- Fix limit comparison under Python3 (#143)
- Do not serialize using JSON if not necessary (#131)
- Fix crash of classic logger with unicode (#142)
- Fix crash of CloudStorage backend when remote returns 500 (#142)
- Fix behaviour of CloudStorage with backslashes in querystring (#142)
- Fix python3.4 segmentation fault (#142)
- Add missing port in Next-Page header (#147)

**Internal changes**

- Use ujson again, it was removed in the 1.3.2 release (#132)
- Add index for as_epoch(last_modified) (#130). Please add the following
  statements to SQL for the migration::

    ALTER FUNCTION as_epoch(TIMESTAMP) IMMUTABLE;
    CREATE INDEX idx_records_last_modified_epoch ON records(as_epoch(last_modified));
    CREATE INDEX idx_deleted_last_modified_epoch ON deleted(as_epoch(last_modified));

- Prevent fetching to many records for one user collection (#130)
- Use UPSERT for the heartbeat (#141)
- Add missing OpenSSL in installation docs (#146)
- Improve tests of basic auth (#128)


1.3.2 (2015-03-20)
------------------

- Revert ujson usage (#132)


1.3.1 (2015-03-20)
------------------

**Bug fixes**

- Fix packaging (#118)


1.3.0 (2015-03-20)
------------------

**New features**

- Add PostgreSQL connection pooling, with new settings
  ``cliquet.storage_pool_maxconn`` and ``cliquet.cache_pool_maxconn``
  (*Default: 50*) (#112)
- Add `StatsD <https://github.com/etsy/statsd/>`_ support,
  enabled with ``cliquet.statsd_url = udp://server:port`` (#114)
- Add `Sentry <http://sentry.readthedocs.org>`_ support,
  enabled with ``cliquet.sentry_url = http://user:pass@server/1`` (#110)

**Bug fixes**

- Fix FxA verification cache not being used (#103)
- Fix heartbeat database check (#109)
- Fix PATCH endpoint crash if request has no body (#115)

**Internal changes**

- Switch to `ujson <https://pypi.python.org/pypi/ujson>`_ for JSON
  de/serialization optimizations (#108)


1.2.1 (2015-03-18)
------------------

- Fix tests about unicode characters in BATCH querystring patch
- Remove CREATE CAST for the postgresql backend
- Fix environment variable override


1.2 (2015-03-18)
----------------

**Breaking changes**

- `cliquet.storage.postgresql` now uses UUID as record primary key (#70)
- Settings ``cliquet.session_backend`` and ``cliquet.session_url`` were
  renamed ``cliquet.cache_backend`` and ``cliquet.cache_url`` respectively.
- FxA user ids are not hashed anymore (#82)
- Setting ``cliquet.retry_after`` was renamed ``cliquet.retry_after_seconds``
- OAuth2 redirect url now requires to be listed in
  ``fxa-oauth.webapp.authorized_domains`` (e.g. ``*.mozilla.com``)
- Batch are now limited to 25 requests by default (#90)

**New features**

- Every setting can be specified via an environment variable
  (e.g. ``cliquet.storage_url`` with ``CLIQUET_STORAGE_URL``)
- Logging now relies on `structlog <http://structlog.org>`_ (#78)
- Logging output can be configured to stream JSON (#78)
- New cache backend for PostgreSQL (#44)
- Documentation was improved on various aspects (#64, #86)
- Handle every backend errors and return 503 errors (#21)
- State verification for OAuth2 dance now expires after 1 hour (#83)

**Bug fixes**

- FxA OAuth views errors are now JSON formatted (#67)
- Prevent error when pagination token has bad format (#72)
- List of CORS exposed headers were fixed in POST on collection (#54)

**Internal changes**

- Added a method in `cliquet.resource.Resource` to override known fields
  (*required by Kinto*)
- Every setting has a default value
- Every end-point requires authentication by default
- Session backend was renamed to cache (#96)


1.1.4 (2015-03-03)
------------------

- Update deleted_field support for postgres (#62)


1.1.3 (2015-03-03)
------------------

- Fix include_deleted code for the redis backend (#60)
- Improve the update_record API (#61)


1.1.2 (2015-03-03)
------------------

- Fix packaging to include .sql files.


1.1.1 (2015-03-03)
------------------

- Fix packaging to include .sql files.


1.1 (2015-03-03)
----------------

**New features**

- Support filter on deleted using since (#51)

**Internal changes**

- Remove python 2.6 support (#50)
- Renamed Resource.deleted_mark to Resource.deleted_field (#51)
- Improve native_value (#56)
- Fixed Schema options inheritance (#55)
- Re-build the virtualenv when setup.py changes
- Renamed storage.url to cliquet.storage_url (#49)
- Refactored the tests/support.py file (#38)


1.0 (2015-03-02)
----------------

- Initial version, extracted from Mozilla Services Reading List project (#1)

**New features**

- Expose CORS headers so that client behind CORS policy can access them (#5)
- Postgresql Backend (#8)
- Use RedisSession as a cache backend for PyFxA (#10)
- Delete multiple records via DELETE on the collection_path (#13)
- Batch default prefix for endpoints (#14 / #16)
- Use the app version in the / endpoint (#22)
- Promote Basic Auth as a proper authentication backend (#37)

**Internal changes**

- Backends documentation (#15)
- Namedtuple for filters and sort (#17)
- Multiple DELETE in Postgresql (#18)
- Improve Resource API (#29)
- Refactoring of error management (#41)
- Default Options for Schema (#47)
