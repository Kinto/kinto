Changelog
#########

This document describes changes between each past release.


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
