Ecosystem
#########

.. note::

    If you build a package that you would like to see listed here, just
    get in touch with us !


Basics about Pyramid apps
=========================

Include external packages
-------------------------

Appart from usual python «*import and use*», *Pyramid* can include external
packages, that can bring views, event listeners etc.

.. code-block:: python
    :emphasize-lines: 7

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize(config, __version__)
        config.scan("myproject.views")

        config.include('cliquet_elasticsearch')

        return config.make_wsgi_app()


Alternatively, packages can also be included via configuration:

.. code-block:: ini

    # myproject.ini
    pyramid.includes = cliquet_elasticsearch
                       pyramid_debugtoolbar

Include me
----------

In order to be included, a package must define an ``includeme`` function.

For example, in :file:`cliquet_elasticsearch/init.py`:

.. code-block:: python

    def includeme(config):
        settings = config.get_settings()

        config.add_view(...)


Custom backend
==============

As a simple example, let's add add another kind of cache backend to *Cliquet*.

:file:`cliquet_riak/cache.py`:

    from cliquet.cache import CacheBase
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
        uri = settings['cliquet.cache_url']
        uri = urlparse.urlparse(uri)

        return Riak(pb_port=uri.port or 8087)


This new backend type can now be specified in application configuration:

.. code-block:: ini

    # myproject.ini
    cliquet.cache_backend = cliquet_riak.cache


Adding features
===============

Another use-case would be to add extra-features, like indexing for example.

* Initialize an indexer ;
* Add a ``/search`` view.
* Index records manipulated by resources ;


:file:`cliquet_indexing/__init__.py`:

.. code-block:: python

    def includeme(config):
        settings = config.get_settings()
        backend = settings.get('cliquet.indexing_backend',
                               'cliquet_indexing.elasticsearch')
        indexer = config.maybe_dotted(backend)
        config.registry.indexer = indexer.load_from_config(config)

        config.scan('cliquet_indexing.views', **kwargs)


:file:`cliquet_indexing/views.py`:

.. code-block:: python

    from cornice import Service

    search = Service(name="search",
                     path='/search/{resource_name}/',
                     description="Search")

    @search.post()
    def get_search(request):
        query = request.body
        resource_name = request.matchdict['resource_name']
        indexer = request.registry.indexer
        results = indexer.search(resource_name, query)

        return results


:file:`cliquet_indexing/resource.py`:

.. code-block:: python

    class IndexedResource(cliquet.resource.BaseResource):
        def create_record(self, record):
            r = super(IndexedResource, self).create_record(self, record)

            indexer = self.request.registry.indexer
            indexer.index_record(self.name, record)

            return r

.. note::

    In this example, ``IndexedResource`` is inherited, and must hence be
    used explicitly as base resource class in applications.
    A nicer pattern would be to trigger *Pyramid* events in *Cliquet* and
    let packages like this one plug listeners. If you're interested,
    `we started to discuss it <https://github.com/mozilla-services/cliquet/issues/32>`_ !


JavaScript client
=================

One of the main goal of *Cliquet* is to ease the development of REST
microservices, most likely to be used in a JavaScript environment.

A client could look like this:

.. code-block:: javascript

    var client = new cliquet.Client({
        server: 'https://api.server.com',
        store: localforage
    });

    var articles = client.resource('/articles');

    articles.create({title: "Hello world"})
      .then(function (result) {
        // success !
      });

    articles.get('id-1234')
      .then(function (record) {
        // Read from local if offline.
      });

    articles.filter({
        'title': {'$eq': 'Hello'}
      })
      .then(function (results) {
        // List of records.
      });

    articles.sync()
      .then(function (result) {
        // Synchronize offline store with server.
      });
