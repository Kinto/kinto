.. _ecosystem:

Ecosystem
#########

This section gathers information about extending *Kinto-Core*, and third-party packages.

Packages
========

* :github:`mozilla-services/kinto-fxa`:
  Add support of :term:`Firefox Accounts` OAuth2 authentication in *Kinto-Core*


.. note::

    If you build a package that you would like to see listed here, just
    get in touch with us!


Extending Kinto-Core
====================

Pluggable components
--------------------

:term:`Pluggable` components can be substituted from configuration files,
as long as the replacement follows the original component API.

.. code-block:: ini

    # myproject.ini
    kinto.logging_renderer = cliquet_fluent.FluentRenderer

This is the simplest way to extend *Kinto-Core*, but will be limited to its
existing components (cache, storage, log renderer, ...).

In order to add extra features, including external packages is the way to go!


Include external packages
-------------------------

Appart from usual python «*import and use*», *Pyramid* can include external
packages, which can bring views, event listeners etc.

.. code-block:: python
    :emphasize-lines: 11

    import kinto.core
    from pyramid.config import Configurator


    def main(global_config, **settings):
        config = Configurator(settings=settings)

        kinto.core.initialize(config, '0.0.1')
        config.scan("myproject.views")

        config.include('kinto_elasticsearch')

        return config.make_wsgi_app()


Alternatively, packages can also be included via configuration:

.. code-block:: ini

    # myproject.ini
    kinto.includes = kinto_elasticsearch
                       pyramid_debugtoolbar


There are `many available packages <curated list>`_, and it is straightforward to build one.

.. _curated list: https://github.com/ITCase/awesome-pyramid


Include me
----------

In order to be included, a package must define an ``includeme(config)`` function.

For example, in :file:`kinto_elasticsearch/init.py`:

.. code-block:: python

    def includeme(config):
        settings = config.get_settings()

        config.add_view(...)


Configuration
-------------

In order to ease the management of settings, *Kinto-Core* provides a helper that
reads values from :ref:`environment variables <configuration-environment>`
and uses default application values.

.. code-block:: python
    :emphasize-lines: 1,2,5-7,11,14,15

    import kinto.core
    from pyramid.settings import asbool


    DEFAULT_SETTINGS = {
        'kinto_elasticsearch.refresh_enabled': False
    }


    def includeme(config):
        kinto.core.load_default_settings(config, DEFAULT_SETTINGS)
        settings = config.get_settings()

        refresh_enabled = settings['kinto_elasticsearch.refresh_enabled']
        if asbool(refresh_enabled):
            ...

        config.add_view(...)


In this example, if the environment variable ``KINTO_ELASTICSEARCH_REFRESH_ENABLED``
is set to ``true``, the value present in configuration file is ignored.



Declare API capabilities
========================

Arbitrary capabilities can be declared and exposed in the :ref:`root URL <api-utilities>`.

Clients can rely on this to detect optional features on the server. For example,
features brought by plugins.


.. code-block:: python
    :emphasize-lines: 7-11

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        kinto.core.initialize(config, __version__)
        config.scan("myproject.views")

        settings = config.get_settings()
        if settings['flush_enabled']:
            config.add_api_capability("flush",
                                      description="Flush server using endpoint",
                                      url="http://kinto.readthedocs.io/en/latest/configuration/settings.html#activating-the-flush-endpoint")

        return config.make_wsgi_app()

.. note::

    Any argument passed to ``config.add_api_capability()`` will be exposed in the
    root URL.


Custom backend
==============

As a simple example, let's add add another kind of cache backend to *Kinto-Core*.

:file:`kinto_riak/cache.py`:

.. code-block:: python

    from kinto.core.cache import CacheBase
    from riak import RiakClient


    class Riak(CacheBase):
        def __init__(self, **kwargs):
            self._client = RiakClient(**kwargs)
            self._bucket = self._client.bucket('cache')

        def set(self, key, value, ttl=None):
            key = self._bucket.new(key, data=value)
            key.store()
            if ttl is not None:
                # ...

        def get(self, key):
            fetched = self._bucked.get(key)
            return fetched.data

        #
        # ...see cache documentation for a complete API description.
        #


    def load_from_config(config):
        settings = config.get_settings()
        uri = settings['kinto.cache_url']
        uri = urlparse.urlparse(uri)

        return Riak(pb_port=uri.port or 8087)


Once its package installed and available in Python path, this new backend type
can be specified in application configuration:

.. code-block:: ini

    # myproject.ini
    kinto.cache_backend = kinto_riak.cache


Adding features
===============

Another use-case would be to add extra-features, like indexing for example.

* Initialize an indexer on startup;
* Add a ``/search/{collection}/`` end-point;
* Index records manipulated by resources.


Inclusion and startup in :file:`kinto_indexing/__init__.py`:

.. code-block:: python

    DEFAULT_BACKEND = 'kinto_indexing.elasticsearch'

    def includeme(config):
        settings = config.get_settings()
        backend = settings.get('kinto.indexing_backend', DEFAULT_BACKEND)
        indexer = config.maybe_dotted(backend)

        # Store indexer instance in registry.
        config.registry.indexer = indexer.load_from_config(config)

        # Activate end-points.
        config.scan('kinto_indexing.views')


End-point definitions in :file:`kinto_indexing/views.py`:

.. code-block:: python

    from cornice import Service

    search = Service(name="search",
                     path='/search/{collection_id}/',
                     description="Search")

    @search.post()
    def get_search(request):
        collection_id = request.matchdict['collection_id']
        query = request.body

        # Access indexer from views using registry.
        indexer = request.registry.indexer
        results = indexer.search(collection_id, query)

        return results


Example indexer class in :file:`kinto_indexing/elasticsearch.py`:

.. code-block:: python

    class Indexer(...):
        def __init__(self, hosts):
            self.client = elasticsearch.Elasticsearch(hosts)

        def search(self, collection_id, query, **kwargs):
            try:
                return self.client.search(index=collection_id,
                                          doc_type=collection_id,
                                          body=query,
                                          **kwargs)
            except ElasticsearchException as e:
                logger.error(e)
                raise

        def index_record(self, collection_id, record, id_field):
            record_id = record[id_field]
            try:
                index = self.client.index(index=collection_id,
                                          doc_type=collection_id,
                                          id=record_id,
                                          body=record,
                                          refresh=True)
                return index
            except ElasticsearchException as e:
                logger.error(e)
                raise


Indexed resource in :file:`kinto_indexing/resource.py`:

.. code-block:: python

    class IndexedModel(kinto.core.resource.Model):
        def create_record(self, record):
            r = super(IndexedModel, self).create_record(self, record)

            self.indexer.index_record(self, record)

            return r

    class IndexedResource(kinto.core.resource.UserResource):
        def __init__(self, request):
            super(IndexedResource, self).__init__(request)
            self.model.indexer = request.registry.indexer

.. note::

    In this example, ``IndexedResource`` must be used explicitly as a
    base resource class in applications.
    A nicer pattern would be to trigger *Pyramid* events in *Kinto-Core* and
    let packages like this one plug listeners. If you're interested,
    `we started to discuss it <https://github.com/mozilla-services/cliquet/issues/32>`_!


JavaScript client
=================

One of the main goal of *Kinto-Core* is to ease the development of REST
microservices, most likely to be used in a JavaScript environment.

A client could look like this:

.. code-block:: javascript

    var client = new kinto.Client({
        server: 'https://api.server.com',
        store: localforage
    });

    var articles = client.resource('/articles');

    articles.create({title: "Hello world"})
      .then(function (result) {
        // success!
      });

    articles.get('id-1234')
      .then(function (record) {
        // Read from local if offline.
      });

    articles.filter({
        title: {'$eq': 'Hello'}
      })
      .then(function (results) {
        // List of records.
      });

    articles.sync()
      .then(function (result) {
        // Synchronize offline store with server.
      })
      .catch(function (err) {
        // Error happened.
        console.error(err);
      });
