Documentation
=============

Put a brief description of 'readinglist'.

API
===

* Retrieve all articles with ``GET`` on ``/v1/articles``
* Create article with ``POST`` on ``/v1/articles``

* Register your device with ``GET`` on ``/v1/articles/<id>``
* Track all devices with ``GET`` on ``/v1/articles/<id>/devices``
* Get device status with ``GET`` on ``/v1/articles/<id>/devices/<name>``
* Modify device status with ``PATCH`` on ``/v1/articles/<id>/devices/<name>``

* Modify article with ``PATCH`` on ``/v1/articles/<id>``
* Delete article with ``DELETE`` on ``/v1/articles/<id>``

The following end-points may suffer changes:

* Filter articles list with ``/v1/articles?where={"status": "unread"}``
* Sort articles list with ``/v1/articles?sort=[("title", -1)]``
* Embed devices informations in articles ``/v1/articles/<id>?embedded={"devices": 1}``


We'll improve the auto-generated documentation at ``/v1/docs/``.


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
* Navigate the client to ``{oauth_uri}/authorization?action=signin&client_id={client_id}&state={state}&scope={scope}``
* Follow OAuth response redirection to ``/v1/fxa-oauth/token``
* Read token in JSON


Run locally
===========

::

    make serve

