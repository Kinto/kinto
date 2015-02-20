Defining your data model
########################

.. _data-model:

In order to define your data model, you need to define a class with some
special attributes. As a simple example::

    from cliquet.resource import BaseResource, ResourceSchema, crud
    import colander


    class MushroomSchema(ResourceSchema):
        name = colander.SchemaNode(colander.String())


    @crud()
    class Mushroom(BaseResource):
        mapping = MushroomSchema()

By doing that, you just defined a Mushroom resource, which will be available at
the `/mushrooms/` endpoint.

It will accept a bunch of operations, defined in the next sections of the
documentation.
