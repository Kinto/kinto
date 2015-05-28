Resource
########

.. _resource:

*Cliquet* provides a basic component to build resource oriented APIs.
In most cases, the main customization consists in defining the schema of the
records for this resource.


Full example
============

.. code-block:: python

    import colander

    from cliquet import resource
    from cliquet import schema
    from cliquet import utils


    class BookmarkSchema(resource.ResourceSchema):
        url = schema.URL()
        title = colander.SchemaNode(colander.String())
        favorite = colander.SchemaNode(colander.Boolean(), missing=False)
        device = colander.SchemaNode(colander.String(), missing='')

        class Options:
            readonly_fields = ('device',)
            unique_fields = ('url',)


    @resource.crud()
    class Bookmark(resource.BaseResource):
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
processing or fetching from storage, the class


.. automodule:: cliquet.resource
    :members:


Custom record ids
=================

By default, records ids are `UUID4 <http://en.wikipedia.org/wiki/Universally_unique_identifier>_`.

A custom record id generator can be set globally in :ref:`configuration`,
or at the resource level:

.. code-block :: python

    from cliquet import resource
    from cliquet import utils
    from cliquet.storage import generators


    class MsecId(generators.Generator):
        def __call__(self):
            return '%s' % utils.msec_time()


    @resource.crud()
    class Mushroom(resource.BaseResource):
        id_generator = MsecId()


Generators objects
::::::::::::::::::

.. automodule:: cliquet.storage.generators
    :members:


Custom Usage
============

.. code-block :: python

    from cliquet import resource


    def get_registry(request=None):
        if request:
            return request.registry

        from pyramid.threadlocal import get_current_registry
        return get_current_registry()


    registry = get_registry()

    flowers = resource.StoredResource(storage=registry.storage,
                                      name='app:flowers')

    flowers.create_record({'name': 'Jonquille', 'size': 30})
    flowers.create_record({'name': 'Amapola', 'size': 18})

    min_size = resource.Filter('size', 20, resource.COMPARISON.MIN)
    records, total = flowers.get_records(filters=[min_size])

    flowers.delete_record(records[0])
