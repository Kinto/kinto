#################
API Documentation
#################


GET /
-----

The returned value is a JSON mapping containing:

- ``hello``: the name of the service (``"reading list"``)
- ``version``: complete version (``"X.Y.Z"``)
- ``url``: absolute URI (without a trailing slash) of the API (*can be used by client to build URIs*)
- ``eos``: date of end of support in ISO 8601 format (``"yyyy-mm-dd"``, null if unknown)
- ``documentation``: The url to the service documentation


GET /__heartbeat__
------------------

Return the status of each service the *reading list* depends on. The returned value is a JSON mapping containing:

- ``database`` true if operational

Return ``200`` if the connection with each service is working properly and ``503`` if something doesn't work.


GET /articles
-------------

**Requires an FxA OAuth authentication**

Returns all articles of the current user.

The returned value is a JSON mapping containing:

- ``items``: the list of articles, with exhaustive attributes

`See all article attributes <https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal#data-model>`_

A ``Total-Records`` header is sent back to indicate the total number of records
included in the response.

A header ``Last-Modified`` will provide the current timestamp of the collection (*see Server timestamps section*).
It is likely to be used by client to provide ``If-Modified-Since`` or ``If-Unmodified-Since`` headers in subsequent requests.


Filtering
:::::::::

**Single value**

* ``/articles?unread=true``

**Multiple values**

* ``/articles?status=1,2``

**Minimum and maxium**

Prefix attribute name with ``min_`` or ``max_``:

* ``/articles?min_word_count=4000``

:note:
    The lower and upper bounds are inclusive (*i.e equivalent to greater or equal*).

**Exclude**

Prefix attribute name with ``not_``:

* ``/articles?not_status=0``

:note:
    Will return an error if an attribute is unknown.

:note:
    The ``Last-Modified`` response header will always be the same as the unfiltered collection.

Sorting
:::::::

* ``/articles?_sort=-last_modified,title``

:note:
    Articles will be ordered by ``-stored_on`` by default (i.e. newest first).

:note:
    Ordering on a boolean field gives ``true`` values first.

:note:
    Will return an error if an attribute is unknown.


Counting
::::::::

In order to count the number of records, by status for example, without fetching
the actual collection, a ``HEAD`` request can be used. The ``Total-Records`` response
header will then provide the total number of records.


Polling for changes
:::::::::::::::::::

The ``_since`` parameter is provided as an alias for ``min_last_modified``
(*greater or equal*).

* ``/articles?_since=123456``

The new value of the collection latest modification is provided in headers (*see Server timestamps section*).

When the since parameter is provided, every deleted articles will appear in the
list with a deleted status (``status=2``).

If the request header ``If-Modified-Since`` is provided, and if the collection has not
suffered changes meanwhile, a ``304 Not Modified`` response is returned.


Pagination
::::::::::

Paging is performed through a ``_limit`` parameter and a ``Next-Page`` response header.

Client should begin by issuing a *GET /articles?_limit=<LIMIT>* request, which
will return up to *<LIMIT>* items.

* ``/articles?_limit=100``

If there were additional items matching the query, the response will be a
``206 Partial Content`` and include a ``Next-Page`` header containing the next
page full URL.

To fetch additional items, the next request is performed on the URL obtained from ``Next-Page`` header.
This process is repeated until the response does not include the ``Next-Page`` header.

:note:
    Using the ``Next-Page`` technique (i.e. `continuation tokens <http://vermorel.com/journal/2010/2/22/paging-indices-vs-continuation-tokens.html>`_)
    the implementation of pagination is completely hidden from clients, and thus
    completely interchangeable.

Pagination on a filtered collection should not be obstructed by modification or creation of non matching records.

To guard against other clients making concurrent changes to the collection, the
next page URL will contain information about the collection obtained on the first
pagination call.

:note:
    Will return an error if limit has invalid values (e.g. non integer or
    above maximum)

:note:
    Will return a ``412 Precondition failed`` error if a modification has occured since
    the first pagination call.

    Pagination should be restarted from the first page, i.e. without pagination
    parameters.


List of available URL parameters
::::::::::::::::::::::::::::::::

- ``<prefix?><attribute name>``: filter by value(s)
- ``_since``: polling changes
- ``_sort``: order list
- ``_limit``: pagination max size

Some additional internal parameters are used by pagination. Client should not
be aware of them, since they are set and provided through the ``Next-Page`` header.

- ``_page_token``: pagination continuation token


Combining all parameters
::::::::::::::::::::::::

Filtering, sorting and paginating can all be combined together.

* ``/articles?_sort=-last_modified&_limit=100``


POST /articles
--------------

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
::::::::::

If the posted values are invalid (e.g. *added_on is not an integer*) an error response is returned with status ``400``. `See details on error responses <https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal#error-responses>`_.


:note:
    The ``status`` can take only ``0`` (OK) and ``1`` (archived), even though
    the server sets it to ``2`` when including deleted articles in the collection.

:note:
    *(undecided)* For some cases, it can make sense for the server to fix arbitrarily
    validation errors on records (e.g. truncating long titles).


Conflicts
:::::::::

Articles URL are unique per user (both ``url`` and ``resolved_url``).

:note:
    A ``url`` always resolves towards the same URL. If ``url`` is not unique, then
    its ``resolved_url`` won't either.

:note:
    Unicity on URLs is determined the full URL, including location hash.
    (e.g. http://news.com/day-1.html#paragraph1, http://spa.com/#/content/3)

:note:
    Deleted items should be taken into account for URL unicity.

If an article is created with an URL that already exists, a ``303 See Other`` response
is returned to indicate the existing record.

The response body is a JSON mapping, with the following attribute:

- ``id``: the id of the conflicting record


GET /articles/<id>
------------------

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
---------------------

**Requires an FxA OAuth authentication**

Delete a specific article by its id.

The DELETE response is the record that was deleted.

If the record is missing (or already deleted), a ``404 Not Found`` is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    Once deleted, an article will appear in the collection with a deleted status
    (``status=2``) and will have most of its fields empty.

:note:
    The server will have to implement an internal mechanism to will keep track of deleted items,
    and purge them eventually.


PATCH /articles/<id>
--------------------

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

:note:
    ``read_position`` can only be changed for a greater value than the current one.

:note:
    If ``unread`` is changed to false, ``marked_read_on`` and ``marked_read_by`` are expected to be provided.

:note:
    If ``unread`` was already false, ``marked_read_on`` and ``marked_read_by`` are not updated with provided values.

:note:
    If ``unread`` is changed to true, ``marked_read_by`` and ``marked_read_on``
    are changed automatically to null.

:note:
    As mentionned in the *Validation section*, an article status cannot take the value ``2``.


Conflicts
:::::::::

*(Draft)*

If the modification of ``resolved_url`` introduces a conflict, because another
record violates unicity, a ``409 Conflict`` error response is returned.

The error attributes will be set:

- ``info``: the URL of the conflicting record


Batch operations
================

**Requires an FxA OAuth authentication**

POST /batch
-----------

The POST body is a mapping, with the following attributes:

- ``requests``: the list of requests
- ``defaults``: (*optional*) values in common for all requests

 Each request is a JSON mapping, with the following attribute:

- ``method``: HTTP verb
- ``path``: URI
- ``body``: a mapping
- ``headers``: (*optional*), otherwise take those of batch request

::

    {
      "defaults": {
        "method" : "POST",
        "path" : "/articles",
        "headers" : {
          ...
        }
      },
      "requests": [
        {
          "body" : {
            "title": "MoFo",
            "url" : "http://mozilla.org"
          }
        },
        {
          "body" : {
            "title": "MoCo",
            "url" : "http://mozilla.com"
          }
        },
        {
          "method" : "PATCH",
          "path" : "/articles/409",
          "body" : {
            "read_position" : 3477
          }
        }
      ]
    ]

The response body is a list of all responses:

::

    {
      "defaults": {
        "path" : "/articles",
      },
      "responses": [
        {
          "path" : "/articles/409",
          "status": 200,
          "body" : {
            "id": 409,
            "url": "...",
            ...
            "read_position" : 3477
          },
          "headers": {
            ...
          }
        },
        {
          "status": 201,
          "body" : {
            "id": 411,
            "title": "MoFo",
            "url" : "http://mozilla.org",
            ...
          },
        },
        {
          "status": 201,
          "body" : {
            "id": 412,
            "title": "MoCo",
            "url" : "http://mozilla.com",
            ...
          },
        },
      ]
    ]


:note:
     The responses are not necessarily in the same order of the requests.


Pros & Cons
:::::::::::

* This respects REST principles
* This is easy for the client to handle, since it just has to pile up HTTP requests while offline
* It looks to be a convention for several REST APIs (`Neo4J <http://neo4j.com/docs/milestone/rest-api-batch-ops.html>`_, `Facebook <https://developers.facebook.com/docs/graph-api/making-multiple-requests>`_, `Parse <https://parse.com/docs/rest#objects-batch>`_)
* Payload of response can be heavy, especially while importing huge collections


Massive operations
------------------

*(Undecided, Draft)*

In order to limit the size of reponses payloads, a request header ``Light-Response``
can be added. Only ``status`` and ``body`` attributes will be returned,
and only fields specified in the header will be included.

For example, with ``Light-Response: id, stored_on, errno, info``:
::

    {
      "responses": [
        {
          "status": 200,
          "body" : {
            "id": "409",
            "stored_on": "1234567"
          }
        },
        {
          "status": 201,
          "body" : {
            "id": 412,
            "stored_on": "988767568"
          }
        },
        {
          "status": 409,
          "body" : {
            "errno": 122,
            "info": "http://server/v1/articles/970",
          }
        },
        {
          "status": 303,
          "body" : {
            "id": "667",
          }
        }
      ]
    ]
