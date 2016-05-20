Changelog
#########

This document describes changes between each past release.

2.1.2 (2016-05-20)
==================

**Bug fixes**

- Fix crash when a cache expires setting is set for a specific bucket or collection.
- Redirects version prefix to hello page when trailing_slash_redirect is enabled. (mozilla-services/cliquet#700)
- Fix crash when setting empty permission list with PostgreSQL permission backend (#575)
- Fix crash when type of values in querystring for exclude/include is wrong (#587)
- Fix crash when providing duplicated principals in permissions with PostgreSQL permission backend (#702)
- Prevent the browser to cache server responses between two sessions. (#593)


2.1.1 (2016-04-29)
==================

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
==================

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


2.0.0 (2016-03-08)
==================

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

Protocol is now in version **1.4**. See `API changelog <http://kinto.readthedocs.io/en/latest/api/>`_.

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
  `See more details <http://cliquet.readthedocs.io/en/latest/reference/notifications.html>`_.
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
===================

**Bug fixes**

- Expose the ETag header in 304 responses for default bucket (ref mozilla-services/cliquet#631)

**Documentation**

- Add Scalingo *one-click deploy* button (#418, thanks @yannski)
- Improve introduction of notifications tutorial (#419, thanks @tarekziade)
- Fix typos (thanks @magopian)


1.11.1 (2016-02-01)
===================

**Bug fixes**

- Fix wheels for Python 3 that were requiring the functools32 package that is
  for Python 2 only (fixes #303).

**Documentation**

- Fix a broken hyperlink in the overview section. (#406, thanks William Hoang)
- Talk about tokens rather than user:password (#393)


1.11.0 (2016-01-28)
===================

**Protocol**

- Forward slashes (``/``) are not escaped anymore in JSON responses (mozilla-services/cliquet#537)
- Fields can be filtered in GET requests using ``_fields=f1,f2`` in querystring (#399)
- New collections can be created via ``POST`` requests (thanks John Giannelos)
- The API capabilities can be exposed in a ``capabilities`` attribute in the
  root URL (#628). Clients can rely on this to detect optional features on the
  server (e.g. enabled plugins)

Protocol is now version 1.3. See `API changelog <http://kinto.readthedocs.io/en/latest/api/>`_.

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
- Add tutorial how to setup Github authentication (#390)
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
===================

**Bug fixes**

- Fix ``kinto init`` when containing folder does not exist (fixes #302)

**Internal changes**

- Added Hoodie in the comparison matrix (#282, thanks @Niraj8!)
- Added a get started button in documentation (#315, thanks @Niraj8!)


1.10.0 (2015-12-01)
===================

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
==================

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

- Optimization for obtention of user principals (#263)
- Do not build the Docker container when using Docker Compose.
- Add Python 3.5 on TravisCI
- Add schema validation loadtest (fixes #201)
- Multiple documentation improvements.
- The PostgreSQL backends now use SQLAlchemy sessions.

See also `*Cliquet* changes <https://github.com/mozilla-services/cliquet/releases/2.11.0>`_


1.8.0 (2015-10-30)
==================

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
==================

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
==================

**Bug fixes**

- Handle 412 details with default bucket (#226)


1.6.1 (2015-10-22)
==================

- Upgraded to *Cliquet* 2.8.2

**Bug fixes**

- Return a JSON body for 405 response on the default bucket (#214)

**Internal changes**

- Improve documentation for new comers (#217)
- Do not force host in default configuration (#219)
- Use tox installed in virtualenv (#221)
- Skip python versions unavailable in tox (#222)


1.6.0 (2015-10-14)
==================

- Upgraded to *Cliquet* 2.8.1

**Breaking changes**

- Settings prefixed with ``cliquet.`` are now deprecated, and should be replaced
  with non prefixed version instead.
- In the root url response, public settings are exposed without prefix too
  (e.g. ``batch_max_requests``).


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
- Fix URL of readthedocs.io (#90)


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
  to use PostgreSQL instead of *Redis* (see default ``config/kinto.ini``)
- ``cliquet.basic_auth_enabled`` is now deprecated (`see *Cliquet*
  docs to enable authentication backends
  <http://cliquet.readthedocs.io/en/latest/reference/configuration.html#basic-auth>`_)


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
