.. _resource:

Resource
########

*Cliquet* provides a basic component to build resource oriented APIs.
In most cases, the main customization consists in defining the schema of the
records for this resource.


Full example
============

.. code-block:: python

    import colander

    from cliquet import resource
    from cliquet import utils


    class BookmarkSchema(resource.ResourceSchema):
        url = colander.SchemaNode(colander.String(), validator=colander.url)
        title = colander.SchemaNode(colander.String())
        favorite = colander.SchemaNode(colander.Boolean(), missing=False)
        device = colander.SchemaNode(colander.String(), missing='')

        class Options:
            readonly_fields = ('device',)
            unique_fields = ('url',)


    @resource.register()
    class Bookmark(resource.UserResource):
        mapping = BookmarkSchema()

        def process_record(self, new, old=None):
            if new['device'] != old['device']:
                new['device'] = self.request.headers.get('User-Agent')

            return new

See the :github:`ReadingList <mozilla-services/readinglist>` and
:github:`Kinto <mozilla-services/kinto>` projects source code for real use cases.


.. _resource-schema:

Resource Schema
===============

Override the base schema to add extra fields using the `Colander API <http://docs.pylonsproject.org/projects/colander/>`_.

.. code-block:: python

    class Movie(ResourceSchema):
        director = colander.SchemaNode(colander.String())
        year = colander.SchemaNode(colander.Int(),
                                   validator=colander.Range(min=1850))
        genre = colander.SchemaNode(colander.String(),
                                    validator=colander.OneOf(['Sci-Fi', 'Comedy']))

.. automodule:: cliquet.schema
    :members:


.. _resource-class:

Resource class
==============

In order to customize the resource URLs or behaviour on record
processing, the resource class can be extended:

.. autoclass:: cliquet.resource.UserResource
    :members:

Interaction with storage
------------------------

In order to customize the interaction of a HTTP resource with its storage,
a custom collection can be plugged-in:

.. code-block:: python

    from cliquet import resource


    class TrackedModel(resource.Model):
        def create_record(self, record, parent_id=None, unique_fields=None):
            record = super(TrackedModel, self).create_record(record,
                                                             parent_id,
                                                             unique_fields)
            trackid = index.track(record)
            record['trackid'] = trackid
            return record


    class Payment(resource.UserResource):
        default_model = TrackedModel


.. _resource-model:

.. autoclass:: cliquet.resource.Model
    :members:


Custom record ids
=================

By default, records ids are `UUID4 <http://en.wikipedia.org/wiki/Universally_unique_identifier>_`.

A custom record ID generator can be set globally in :ref:`configuration`,
or at the resource level:

.. code-block:: python

    from cliquet import resource
    from cliquet import utils
    from cliquet.storage import generators


    class MsecId(generators.Generator):
        def __call__(self):
            return '%s' % utils.msec_time()


    @resource.register()
    class Mushroom(resource.UserResource):
        def __init__(request):
            super(Mushroom, self).__init__(request)
            self.model.id_generator = MsecId()


Generators objects
------------------

.. automodule:: cliquet.storage.generators
    :members:


Custom Usage
============

Within views
------------

In views, a ``request`` object is available and allows to use the storage
configured in the application:

.. code-block:: python

    from cliquet import resource

    def view(request):
        registry = request.registry

        flowers = resource.Model(storage=registry.storage,
                                 collection_id='app:flowers')

        flowers.create_record({'name': 'Jonquille', 'size': 30})
        flowers.create_record({'name': 'Amapola', 'size': 18})

        min_size = resource.Filter('size', 20, resource.COMPARISON.MIN)
        records, total = flowers.get_records(filters=[min_size])

        flowers.delete_record(records[0])


Outside views
-------------

Outside views, an application context has to be built from scratch.

As an example, let's build a code that will copy a collection into another:

.. code-block:: python

    from cliquet import resource, DEFAULT_SETTINGS
    from pyramid import Configurator


    config = Configurator(settings=DEFAULT_SETTINGS)
    config.add_settings({
        'cliquet.storage_backend': 'cliquet.storage.postgresql'
        'cliquet.storage_url': 'postgres://user:pass@db.server.lan:5432/dbname'
    })
    cliquet.initialize(config, '0.0.1')

    local = resource.Model(storage=config.registry.storage,
                           parent_id='browsing',
                           collection_id='history')

    remote = resource.Model(storage=config_remote.registry.storage,
                            parent_id='',
                            collection_id='history')

    records, total = in remote.get_records():
    for record in records:
        local.create_record(record)
