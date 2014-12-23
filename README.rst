Documentation
=============

Reading list is a service that help to synchronize articles url in between device of the same person.

API Design
==========

You can look at the API design here: https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal

Implemented API
===============

We have auto-generated documentation at ``/v1/docs/``.


GET /devices
------------

**Requires an FxA Oauth authentication**

Returns all devices of a given user.
The returned value is a json mapping containing:

- **_items**: the list of devices


POST /devices
--------------

**Requires an FxA Oauth authentication**

Used to post a device to the server. The POST body is a Json
mapping containing:

- **name**: device name


DELETE /devices/<id>
--------------------

**Requires an FxA Oauth authentication**

Delete a specific device by its id.


GET /articles
-------------

**Requires an FxA Oauth authentication**

Returns all articles of a given user.
The returned value is a json mapping containing:

- **_items**: the list of articles


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


DELETE /articles/<id>
---------------------

**Requires an FxA Oauth authentication**

Delete a specific article by its id.


PATCH /articles/<id>
--------------------

**Requires an FxA Oauth authentication**

Modify a specific article by its id. The PATCH body is a Json
mapping containing a subset of articles fields.


GET /articles/<id>/status
-------------------------

**Requires an FxA Oauth authentication**

Returns all articles of a given user.
The returned value is a json mapping containing:

- **_items**: the list of devices and status


POST /articles/<id>/status
--------------------------

**Requires an FxA Oauth authentication**

Modify read status of a given device. The POST body is a Json
mapping containing:

- **device_id** (integer): device id
- **read** (integer): the percentage read of this article on this device


GET /articles/<id>/status/<device-id>
-------------------------------------

**Requires an FxA Oauth authentication**

Returns the read status of a given device.
The returned value is a json mapping containing:

- **read** (integer): the percentage read of this article on this device


PATCH /articles/<id>/status/<device-id>
---------------------------------------

**Requires an FxA Oauth authentication**

Modify read status of a given device. The PATCH body is a Json
mapping containing:

- **read** (integer): the percentage read of this article on this device


Authentication
==============


OAuth token
-----------

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
