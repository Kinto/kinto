Viewsets
########

*Cliquet* maps URLs and permissions to resources using *ViewSets*.

View sets can be viewed as a set of rules which can be applied to a resource in
order to define what should be inserted in the routing mechanism of pyramid.


Configuring your viewset
========================

To use *Cliquet* in a basic fashion, you probably don't need to understand how
viewsets work in full detail, but you could extend them very simply.

Default viewset can be extended by passing viewset arguments to the
`resource.register` class decorator:

.. code-block:: python

    from cliquet import resource


    @resource.register(validate_shema_for('POST', 'PUT', 'PATCH'))
    class Resource(resource.BaseResource):
        mapping = BookmarkSchema()


Creating your own viewset
=========================

In case this isn't enough to update the default properties, you can also define
you own viewset and pass it during the registration phase:


.. code-block:: python

    from cliquet import resource


    class MyViewSet(resource.ViewSet):

        def get_service_name(self, endpoint_type, resource):
            """Returns the name of the service, depending a given type and
            resource.
            """
            # Get the resource name from an akwards location.
            return name


    @resource.register(viewset=MyViewSet())
    class Resource(resource.BaseResource):
        mapping = BookmarkSchema()


ViewSet class
=============

In order to customize the resource URLs or permissions, the viewset class can
be extended:

.. autoclass:: cliquet.resource.ViewSet
    :members:
