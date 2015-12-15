.. _viewset:

Viewsets
########

*Cliquet* maps URLs, :term:`endpoints` and :term:`permissions` to resources
using *ViewSets*.

Since a resource defines two URLs with several HTTP methods, a view set can
be considered as a set of rules for registring the resource views into the
routing mechanism of Pyramid.

To use *Cliquet* in a basic fashion, there is no need to understand how
viewsets work in full detail.


Override defaults
=================

Viewsets defaults can be overriden by passing arguments to the
:func:`cliquet.resource.register` class decorator:

.. code-block:: python

    from cliquet import resource


    @resource.register(collection_methods=('GET',))
    class Resource(resource.UserResource):
        mapping = BookmarkSchema()


Subclassing
===========

In case this isn't enough, the :class:`cliquet.resource.viewset.ViewSet` class
can be subclassed and specified during registration:


.. code-block:: python
    :emphasize-lines: 10

    from cliquet import resource


    class NoSchemaViewSet(resource.ViewSet):

        def get_record_schema(self, resource_cls, method):
            simple_mapping = colander.MappingSchema(unknown='preserve')
            return simple_mapping


    @resource.register(viewset=NoSchemaViewSet())
    class Resource(resource.UserResource):
        mapping = BookmarkSchema()


ViewSet class
=============

.. autoclass:: cliquet.resource.ViewSet
    :members:
