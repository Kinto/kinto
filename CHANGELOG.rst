Changelog
=========

This document describes changes between each past release.


1.0 (unreleased)
----------------

- Initial version, extracted from Mozilla Services Reading List project (#1)
- Expose CORS headers so that client behind CORS policy can access them (#5)
- Postgresql Backend (#8)
- Use RedisSession as a cache backend for PyFxA (#10)
- Delete multiple records via DELETE on the collection_path (#13)
- Automatically add the API_PREFIX if missing (#14)
- Documentation on the backends (#15)
- Batch default prefix review (#16)
- Namedtuple for filters and sort (#17)
- Multiple DELETE in Postgresql (#18)
- Use the app version in the / endpoint (#22)
- Improve Resource API (#29)
- Legitimate Basic Auth as an authentication backend (#37)
- Refactoring of error management (#41)
- Default Options for Schema (#47)
