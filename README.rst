Documentation
=============

Put a brief description of 'readinglist'.

API
===

    We have auto-generated documentation at ``/v1/docs/``.


GET /articles
-------------

**Requires an FxA Oauth authentication**

Returns all articles of a given user.
The returned value is a json mapping containing:

- **_items**: the list of articles

Filtering
~~~~~~~~~

**/articles?where={"status": "unread"}**

Sorting
~~~~~~~

**/articles?sort=[("title", -1)]**


POST /articles
--------------

**Requires an FxA Oauth authentication**

Used to post an article to the server. The POST body is a Json
mapping containing:

- **title**: readable title
- **url**: full url


GET /articles/<id>
------------------

**Requires an FxA Oauth authentication**

Returns a specific article by its id.

.. notes::

    With the current behaviour, this operation will associate a device
    to this article.


DELETE /articles/<id>
---------------------

**Requires an FxA Oauth authentication**

Delete a specific article by its id.


PATCH /articles/<id>
--------------------

**Requires an FxA Oauth authentication**

Modify a specific article by its id. The PATCH body is a Json
mapping containing a subset of articles fields.


Embedded devices status
~~~~~~~~~~~~~~~~~~~~~~~

**/articles/<id>?embedded={"devices": 1}**


GET /articles/<id>/devices
--------------------------

**Requires an FxA Oauth authentication**

Returns all articles of a given user.
The returned value is a json mapping containing:

- **_items**: the list of devices and status


GET /articles/<id>/devices/<name>
---------------------------------

**Requires an FxA Oauth authentication**

Returns the read status of a given device.
The returned value is a json mapping containing:

- **read** (integer): the percentage read of this article on this device


PATCH /articles/<id>/devices/<name>
-----------------------------------

**Requires an FxA Oauth authentication**

Modify read status of a given device. The PATCH body is a Json
mapping containing:

- **read** (integer): the percentage read of this article on this device


Authentication
==============

In your requests, use the OAuth token with this header:

::

    Authorization: Bearer <token>


Obtain token manually
~~~~~~~~~~~~~~~~~~~~~

* Go to ``/v1/fxa-oauth/login``
* After submitting the Firefox Account login form, you are redirected
  to ``/v1/fxa-oauth/token``, which provides the OAuth token.


Obtain token using API
~~~~~~~~~~~~~~~~~~~~~~

* Obtain Firefox Account parameters and state in JSON at ``/v1/fxa-oauth/params``
* Navigate the client to ``<oauth_uri>/authorization?action=signin&client_id=<client_id>&state=<state>&scope=<scope>``
* Follow OAuth response redirection to ``/v1/fxa-oauth/token``
* Read token in JSON


Run locally
===========

::

    make serve
