Resource
########

.. _resource-class:

.. automodule:: cliquet.resource
    :members:


Example
=======

.. code-block :: python

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


    @resource.crud()
    class Bookmark(resource.BaseResource):
        mapping = BookmarkSchema()

        def process_record(self, new, old=None):
            if new['device'] != old['device']:
                new['device'] = self.request.headers.get('User-Agent')

            return new
