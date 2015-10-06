Changelog
#########

This document describes changes between each past release.


1.5.1 (2015-10-07)
==================

- Upgraded to *Cliquet* 2.7.0


1.5.0 (2015-09-23)
==================

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
==================

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
==================

- Upgraded to *Cliquet* 2.3.1

**Bug fixes**

- Make sure the default route only catch /buckets/default and
  /buckets/default/* routes. (#131)


1.3.0 (2015-07-13)
==================

- Upgraded to *Cliquet* 2.3.0

**Bug fixes**

- Handle CORS with the default bucket. (#126, #135)
- Add a test to make sure the tutorial works. (#118)

**Internal changes**

- List StatsD counters and timers in documentation (fixes #73)
- Update virtualenv dependencies on setup.py modification (fixes #130)


1.2.1 (2015-07-08)
==================

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
==================

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
- Fix URL of readthedocs.org (#90)


1.1.0 (2015-06-29)
==================

**New features**

- Polish default kinto configuration and default to memory backend. (#81)
- Add the kinto group finder (#78)
- Flush endpoint now returns 404 is disabled (instead of 405) (#82)


**Bug fixes**

- ETag not updated on collection update (#80)


**Internal changes**

- Use py.test to run tests instead of nose (#85)


1.0.0 (2015-06-17)
==================

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
  to use PostgreSQL instead of *Redis* (see default :file:`config/kinto.ini`)
- ``cliquet.basic_auth_enabled`` is now deprecated (`see *Cliquet*
  docs to enable authentication backends
  <http://cliquet.readthedocs.org/en/latest/reference/configuration.html#basic-auth>`_)


**Internal changes**

- Added documentation about deployment and data durability (#50)
- Added load tests (#30)
- Several improvements in documentation (#51)


0.2.2 (2015-06-04)
==================

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
==================

- Upgraded to *cliquet* 1.4.1

**Bug fixes**

- Rely on Pyramid API to build pagination Next-Url (#147)


0.2 (2015-03-24)
================

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
================

**Initial version**

- Schemaless storage of records
- Firefox Account authentication
- Kinto as a storage backend for *cliquet* applications
