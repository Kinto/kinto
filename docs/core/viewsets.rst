.. _viewset:

Viewsets
########

*Kinto-Core* maps URLs, :term:`endpoints` and :term:`permissions` to resources
using *ViewSets*.

Since a resource defines two URLs with several HTTP methods, a view set can
be considered as a set of rules for registring the resource views into the
routing mechanism of Pyramid.

To use *Kinto-Core* in a basic fashion, there is no need to understand how
viewsets work in full detail.


Override defaults
=================

Viewsets defaults can be overriden by passing arguments to the
:func:`kinto.core.resource.register` class decorator:

.. code-block:: python

    from kinto.core import resource


    @resource.register(collection_methods=('GET',))
    class Bookmark(resource.Resource):
        schema = BookmarkSchema


Subclassing
===========

In case this isn't enough, the :class:`kinto.core.resource.viewset.ViewSet` class
can be subclassed and specified during registration:


.. code-block:: python
    :emphasize-lines: 10

    from kinto.core import resource


    class NoSchemaViewSet(resource.ViewSet):

        def get_record_schema(self, resource_cls, method):
            simple_mapping = colander.MappingSchema(unknown='preserve')
            return simple_mapping


    @resource.register(viewset=NoSchemaViewSet())
    class Resource(resource.Resource):
        schema = BookmarkSchema


ViewSet class
=============

.. autoclass:: kinto.core.resource.viewset.ViewSet
    :members:
