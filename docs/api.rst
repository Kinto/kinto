#################
API Documentation
#################

.. _http-apis:

GET /articles
=============

**Requires an FxA OAuth authentication**

Returns all articles of the current user.

The returned value is a JSON mapping containing:

- ``items``: the list of articles, with exhaustive attributes

`See all article attributes <https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal#data-model>`_

A ``Total-Records`` header is sent back to indicate the estimated
total number of records included in the response.

A header ``Last-Modified`` will provide the current timestamp of the
collection (*see Server timestamps section*).  It is likely to be used
by client to provide ``If-Modified-Since`` or ``If-Unmodified-Since``
headers in subsequent requests.


Filtering
---------

**Single value**

* ``/articles?unread=true``

**Multiple values**

* ``/articles?status=1,2``

**Minimum and maxium**

Prefix attribute name with ``min_`` or ``max_``:

* ``/articles?min_word_count=4000``

:note:
    The lower and upper bounds are inclusive (*i.e equivalent to
    greater or equal*).

**Exclude**

Prefix attribute name with ``not_``:

* ``/articles?not_status=0``

:note:
    Will return an error if an attribute is unknown.

:note:
    The ``Last-Modified`` response header will always be the same as
    the unfiltered collection.

Sorting
-------

* ``/articles?_sort=-last_modified,title``

:note:
    Articles will be ordered by ``-stored_on`` by default (i.e. newest first).

:note:
    Ordering on a boolean field gives ``true`` values first.

:note:
    Will return an error if an attribute is unknown.


Counting
--------

In order to count the number of records, by status for example,
without fetching the actual collection, a ``HEAD`` request can be
used. The ``Total-Records`` response header will then provide the
total number of records.


Polling for changes
-------------------

The ``_since`` parameter is provided as an alias for
``min_last_modified`` (*greater or equal*).

* ``/articles?_since=123456``

The new value of the collection latest modification is provided in
headers (*see Server timestamps section*).

When the since parameter is provided, every deleted articles will
appear in the list with a deleted status (``status=2``).

If the request header ``If-Modified-Since`` is provided, and if the
collection has not suffered changes meanwhile, a ``304 Not Modified``
response is returned.


List of available URL parameters
--------------------------------

- ``<prefix?><attribute name>``: filter by value(s)
- ``_since``: polling changes
- ``_sort``: order list
- ``_limit``: pagination max size

Some additional internal parameters are used by pagination. Client should not
be aware of them, since they are set and provided through the ``Next-Page`` header.

- ``_page_token``: pagination continuation token


Combining all parameters
------------------------

Filtering, sorting and paginating can all be combined together.

* ``/articles?_sort=-last_modified&_limit=100``


POST /articles
==============

**Requires an FxA OAuth authentication**

Used to create an article on the server. The POST body is a JSON
mapping containing:

- ``url``
- ``title``
- ``added_by``

:note:
    Since the device which added the article can differ from the current device
    (e.g. while importing), the device name is not provided through a request header.

The POST response body is the newly created record, if all posted values are valid. Additional optional attributes can also be specified:

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

**Optional values**

- ``added_on``
- ``excerpt``
- ``favorite``
- ``unread``
- ``status``
- ``is_article``
- ``resolved_url``
- ``resolved_title``

**Auto default values**

For v1, the server will assign default values to the following attributes:

- ``id``: *uuid*
- ``resolved_url``: ``url``
- ``resolved_title``: ``title``
- ``excerpt``: empty text
- ``status``: 0-OK
- ``favorite``: false
- ``unread``: true
- ``is_article``: true
- ``last_modified``: current server timestamp
- ``stored_on``: current server timestamp
- ``marked_read_by``: null
- ``marked_read_on``: null
- ``word_count``: null

For v2, the server will fetch the content, and assign the following attributes with actual values:

- ``resolved_url``: the final URL obtained after all redirections resolved
- ``resolved_title``: The fetched page's title (content of <title>)
- ``excerpt``: The first 200 words of the article
- ``word_count``: Total word count of the article


Validation
----------

If the posted values are invalid (e.g. *added_on is not an integer*) an error response is returned with status ``400``. `See details on error responses <https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal#error-responses>`_.


:note:
    The ``status`` can take only ``0`` (OK) and ``1`` (archived), even though
    the server sets it to ``2`` when including deleted articles in the collection.


Conflicts
---------

Articles URL are unique per user (both ``url`` and ``resolved_url``).

:note:
    A ``url`` always resolves towards the same URL. If ``url`` is not unique, then
    its ``resolved_url`` won't either.

:note:
    Unicity on URLs is determined the full URL, including location hash.
    (e.g. http://news.com/day-1.html#paragraph1, http://spa.com/#/content/3)

:note:
    Deleted items should be taken into account for URL unicity.

.. If an article is created with an URL that already exists, a ``303 See Other`` response
   is returned to indicate the existing record.

   The response body is a JSON mapping, with the following attribute:

   - ``id``: the id of the conflicting record


GET /articles/<id>
==================

**Requires an FxA OAuth authentication**

Returns a specific article by its id.

For convenience and consistency, a header ``Last-Modified`` will also repeat the
value of ``last_modified``.

If the request header ``If-Modified-Since`` is provided, and if the record has not
changed meanwhile, a ``304 Not Modified`` is returned.

:note:
    Even though article URLs are unique together, we use the article id field
    to target individual records.


DELETE /articles/<id>
=====================

**Requires an FxA OAuth authentication**

Delete a specific article by its id.

The DELETE response is the record that was deleted.

If the record is missing (or already deleted), a ``404 Not Found`` is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

.. :note:
       Once deleted, an article will appear in the collection with a deleted status
       (``status=2``) and will have most of its fields empty.


PATCH /articles/<id>
====================

**Requires an FxA OAuth authentication**

Modify a specific article by its id. The PATCH body is a JSON
mapping containing a subset of articles fields.

The PATCH response is the modified record (full).

**Modifiable fields**

- ``title``
- ``excerpt``
- ``favorite``
- ``unread``
- ``status``
- ``is_article``
- ``resolved_url``
- ``resolved_title``
- ``read_position``

If the record is missing (or already deleted), a ``404 Not Found`` error is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    ``last_modified`` is updated to the current server timestamp.

:note:
    Changing ``read_position`` never generates conflicts.

.. :note:
       ``read_position`` can only be changed for a greater value than the current one.

.. :note:
       If ``unread`` is changed to false, ``marked_read_on`` and ``marked_read_by`` are expected to be provided.

.. :note:
       If ``unread`` was already false, ``marked_read_on`` and ``marked_read_by`` are not updated with provided values.

:note:
    If ``unread`` is changed to true, ``marked_read_by`` and ``marked_read_on``
    are changed automatically to null.

:note:
    As mentionned in the *Validation section*, an article status cannot take the value ``2``.
