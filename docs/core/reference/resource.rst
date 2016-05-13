.. _resource:

Resource
########

*Kinto-Core* provides a basic component to build resource oriented APIs.
In most cases, the main customization consists in defining the schema of the
records for this resource.


Full example
============

.. code-block:: python

    import colander

    from kinto.core import resource
    from kinto.core import utils


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
            new = super(Bookmark, self).process_record(new, old)
            if new['device'] != old['device']:
                new['device'] = self.request.headers.get('User-Agent')

            return new

See the :github:`ReadingList <mozilla-services/readinglist>` and
:github:`Kinto <mozilla-services/kinto>` projects source code for real use cases.


.. _resource-urls:

URLs
====

By default, a resource defines two URLs:

* ``/{classname}s`` for the list of records
* ``/{classname}s/{id}`` for single records

Since adding an ``s`` suffix for the plural form might not always be relevant,
URLs can be specified during registration:

.. code-block:: python

    @resource.register(collection_path='/user/bookmarks',
                       record_path='/user/bookmarks/{{id}}')
    class Bookmark(resource.UserResource):
        mapping = BookmarkSchema()

.. note::

    The same resource can be registered with different URLs.



Schema
======

Override the base schema to add extra fields using the `Colander API <http://docs.pylonsproject.org/projects/colander/>`_.

.. code-block:: python

    class Movie(ResourceSchema):
        director = colander.SchemaNode(colander.String())
        year = colander.SchemaNode(colander.Int(),
                                   validator=colander.Range(min=1850))
        genre = colander.SchemaNode(colander.String(),
                                    validator=colander.OneOf(['Sci-Fi', 'Comedy']))

See the :ref:`resource schema options <resource-schema>` to define *schema-less* resources or specify rules
for unicity or readonly.


.. _resource-permissions:

Permissions
===========

Using the :class:`kinto.core.resource.UserResource`, the resource is accessible by
any authenticated request, but the records are isolated by :term:`user id`.

In order to define resources whose records are not isolated, open publicly or
controlled with individual fined-permissions, a :class:`kinto.core.resource.ShareableResource`
could be used.

But there are other strategies, please refer to :ref:`dedicated section about permissions
<permissions>`.


HTTP methods and options
========================

In order to specify which HTTP verbs (``GET``, ``PUT``, ``PATCH``, ...)
are allowed on the resource, as well as specific custom Pyramid (or :rtd:`cornice`)
view arguments, refer to the :ref:`viewset section <viewset>`.


Events
======

When a record is created/deleted in a resource, an event is sent.
See the `dedicated section about notifications <notifications>`_ to plug events
in your Pyramid/*Kinto-Core* application or plugin.


Model
=====

Plug custom model
-----------------

In order to customize the interaction of a HTTP resource with its storage,
a custom model can be plugged-in:

.. code-block:: python

    from kinto.core import resource


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


Relationships
-------------

With the default model and storage backend, *Kinto-Core* does not support complex
relations.

However, it is possible to plug a custom :ref:`model class <resource-model>`,
that will take care of saving and retrieving records with relations.

.. note::

    This part deserves more love, `please come and discuss <https://github.com/mozilla-services/cliquet/issues/135>`_!


In Pyramid views
----------------

In Pyramid views, a ``request`` object is available and allows to use the storage
configured in the application:

.. code-block:: python

    from kinto.core import resource

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

    from kinto.core import resource, DEFAULT_SETTINGS
    from pyramid import Configurator


    config = Configurator(settings=DEFAULT_SETTINGS)
    config.add_settings({
        'kinto.storage_backend': 'kinto.core.storage.postgresql'
        'kinto.storage_url': 'postgres://user:pass@db.server.lan:5432/dbname'
    })
    kinto.core.initialize(config, '0.0.1')

    local = resource.Model(storage=config.registry.storage,
                           parent_id='browsing',
                           collection_id='history')

    remote = resource.Model(storage=config_remote.registry.storage,
                            parent_id='',
                            collection_id='history')

    records, total = in remote.get_records():
    for record in records:
        local.create_record(record)


Custom record ids
=================

By default, records ids are `UUID4 <http://en.wikipedia.org/wiki/Universally_unique_identifier>`_.

A custom record ID generator can be set globally in :ref:`configuration`,
or at the resource level:

.. code-block:: python

    from kinto.core import resource
    from kinto.core import utils
    from kinto.core.storage import generators


    class MsecId(generators.Generator):
        def __call__(self):
            return '%s' % utils.msec_time()


    @resource.register()
    class Mushroom(resource.UserResource):
        def __init__(request):
            super(Mushroom, self).__init__(request)
            self.model.id_generator = MsecId()


Python API
==========

.. _resource-class:

Resource
--------

.. autoclass:: kinto.core.resource.UserResource
    :members:

.. _resource-schema:

Schema
------

.. automodule:: kinto.core.resource.schema
    :members:

.. _resource-model:

Model
-----

.. autoclass:: kinto.core.resource.Model
    :members:

Generators
----------

.. automodule:: kinto.core.storage.generators
    :members:
