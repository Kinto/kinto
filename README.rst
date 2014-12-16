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

* Filter articles list with ``/v1/articles?where={"status": "unread"}``
* Sort articles list with ``/v1/articles?sort=[("title", -1)]``


We'll improve the auto-generated documentation at ``/v1/docs/``.
