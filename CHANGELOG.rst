Changelog
#########

This document describes changes between each past release.


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
