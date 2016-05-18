.. _tutorial-write-plugin:

How to write a Kinto plugin?
============================

*Kinto* plugins allow to add extra-features to *Kinto*. Most notably:

* Respond to internal events (e.g. notify third-party)
* Add endpoints for custom URLs (e.g. new hook URL)
* Add custom endpoint renderers (e.g. XML instead of JSON)

*Kinto* plugins are :ref:`Python modules loaded on startup <configuration-plugins>`.

In this tutorial, we will build a plugin for `ElasticSearch <https://en.wikipedia.org/wiki/Elasticsearch>`_,
a full-text search engine. The plugin will:

* Initialize an indexer on startup;
* Index the records when they're created, updated, or deleted.
* Add a new ``/{collection}/search`` endpoint;

Plugins are built using the Pyramid ecosystem.


Run ElasticSearch
-----------------

We will run a local install of *ElasticSearch* on ``localhost:9200``.

Using Docker it is pretty straightforward:

::

    sudo docker run -p 9200:9200 elasticsearch

It is also be installed manually using the `official instructions <https://www.elastic.co/downloads/elasticsearch>`_.


Include me
----------

First, create a Python package and install it locally. For example:

::

    $ pip install cookiecutter
    $ cookiecutter gh:kragniz/cookiecutter-pypackage-minimal

    [...]

    $ cd kinto_elasticsearch
    $ python setup.py develop

In order to be included, a package must define an ``includeme(config)`` function.

For example, in :file:`kinto_elasticsearch/__init__.py`:

.. code-block:: python

    def includeme(config):
        print("I am the ElasticSearch plugin!")


Add it the :file:`config.ini` file:

.. code-block:: ini

    kinto.includes = kinto_elasticsearch

Our message should now appear on ``kinto start``.


Simple indexer
--------------

Let's define a simple indexer class in :file:`kinto_elasticsearch/indexer.py`.
It can search and index records, using the official Python package:

::

    $ pip install elasticsearch

It is a wrapper basically, and the code is kept simple for the simplicity of this tutorial:

.. code-block:: python

    import elasticsearch

    class Indexer(object):
        def __init__(self, hosts):
            self.client = elasticsearch.Elasticsearch(hosts)

        def search(self, bucket_id, collection_id, query, **kwargs):
            indexname = '%s-%s' % (bucket_id, collection_id)
            return self.client.search(index=indexname,
                                      doc_type=indexname,
                                      body=query,
                                      **kwargs)

        def index_record(self, bucket_id, collection_id, record, id_field='id'):
            indexname = '%s-%s' % (bucket_id, collection_id)
            if not self.client.indices.exists(index=indexname):
                self.client.indices.create(index=indexname)

            record_id = record[id_field]
            index = self.client.index(index=indexname,
                                      doc_type=indexname,
                                      id=record_id,
                                      body=record,
                                      refresh=True)
            return index

        def unindex_record(self, bucket_id, collection_id, record, id_field='id'):
            indexname = '%s-%s' % (bucket_id, collection_id)
            record_id = record[id_field]
            result = self.client.delete(index=indexname,
                                        doc_type=indexname,
                                        id=record_id,
                                        refresh=True)
            return result


And a simple method to load from configuration:

.. code-block:: python

    from pyramid.settings import aslist

    def load_from_config(config):
        settings = config.get_settings()
        hosts = aslist(settings.get('elasticsearch.hosts', 'localhost:9200'))
        indexer = Indexer(hosts=hosts)
        return indexer


Initialize on startup
---------------------

We now need to initialize the indexer when Kinto starts. It happens in the
``includeme()`` function.

.. code-block:: python
    :emphasize-lines: 5

    from . import indexer

    def includeme(config):
        # Register a global indexer object
        config.registry.indexer = indexer.load_from_config(config)


Add a search view
-----------------

Add an endpoint definition in :file:`kinto_elasticsearch/views.py`:

.. code-block:: python

    from kinto.core import Service, logger

    search = Service(name="search",
                     path='/buckets/{bucket_id}/collections/{collection_id}/search',
                     description="Search")

    @search.post()
    def get_search(request):
        bucket_id = request.matchdict['bucket_id']
        collection_id = request.matchdict['collection_id']

        query = request.body

        # Access indexer from views using registry.
        indexer = request.registry.indexer
        try:
            results = indexer.search(bucket_id, collection_id, query)
        except Exception as e:
            logger.exception(e)
            results = {}
        return results

Enable the view:

.. code-block:: python
    :emphasize-lines: 7,8

    from . import indexer

    def includeme(config):
        # Register a global indexer object
        config.registry.indexer = indexer.load_from_config(config)

        # Activate end-points.
        config.scan('kinto_elasticsearch.views')

This new URL should now be accessible, but return no result:

::

     $ http POST "http://localhost:8888/v1/buckets/example/collections/notes/search

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 2
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 20 Jan 2016 12:01:50 GMT
    Server: waitress

    {}


Index records on change
-----------------------

When records change, we index them. When they are deleted, we unindex them.

Let's define a function ``on_resource_changed()`` that will be called when
an action is performed on records.

.. code-block:: python
    :emphasize-lines: 2,19-23

    def on_resource_changed(event):
        indexer = event.request.registry.indexer

        resource_name = event.payload['resource_name']

        if resource_name != "record":
            return

        bucket_id = event.payload['bucket_id']
        collection_id = event.payload['collection_id']

        action = event.payload['action']
        for change in events.impacted_records:
            if action == 'delete':
                indexer.unindex_record(bucket_id,
                                       collection_id,
                                       record=change['old'])
            else:
                indexer.index_record(bucket_id,
                                     collection_id,
                                     record=change['new'])

And then we bind this function with the *Kinto-Core* events:

.. code-block:: python
    :emphasize-lines: 1,12,13

    from kinto.core.events import ResourceChanged

    from . import indexer

    def includeme(config):
        # Register a global indexer object
        config.registry.indexer = indexer.load_from_config(config)

        # Activate end-points.
        config.scan('kinto_elasticsearch.views')

        # Plug the callback with resource events.
        config.add_subscriber(on_resource_changed, ResourceChanged)



Test it altogether
------------------

We're almost done! Now, let's check if it works properly.

Create a bucket and collection:

::

    $ http --auth token:alice-token --verbose PUT http://localhost:8888/v1/buckets/example
    $ http --auth token:alice-token --verbose PUT http://localhost:8888/v1/buckets/example/collections/notes

Add a new record:

::

    $ echo '{"data": {"note": "kinto"}}' | http --auth token:alice-token --verbose POST http://localhost:8888/v1/buckets/example/collections/notes/records

It should now be possible to search for it:

::

    $ http --auth token:alice-token --verbose POST http://localhost:8888/v1/buckets/default/collections/assets/search

.. code-block:: http
    :emphasize-lines: 20-24

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 333
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 20 Jan 2016 12:02:05 GMT
    Server: waitress

    {
        "_shards": {
            "failed": 0,
            "successful": 5,
            "total": 5
        },
        "hits": {
            "hits": [
                {
                    "_id": "453ff779-e967-4b08-99b9-5c16af865a67",
                    "_index": "example-assets",
                    "_score": 1.0,
                    "_source": {
                        "id": "453ff779-e967-4b08-99b9-5c16af865a67",
                        "last_modified": 1453291301729,
                        "note": "kinto"
                    },
                    "_type": "example-assets"
                }
            ],
            "max_score": 1.0,
            "total": 1
        },
        "timed_out": false,
        "took": 20
    }


Going further
-------------

This plugins implements the basic functionnality. In order to make it a first-class
plugin, it would require:

* Check that user has ``read`` permission on the collection before searching
* Create the index when the collection is created
* Create a mapping if the collection has a JSON schema
* Delete the index when the bucket or collection are deleted

If you feel like doing it, we would be very glad to help you!
