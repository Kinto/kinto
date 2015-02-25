from cliquet.resource import crud, BaseResource


@crud(path="/collections/{collection_id}/records/{id}",
      collection_path="/collections/{collection_id}/records")
class Collection(BaseResource):

    @property
    def name(self):
        return self.request.matchdict['collection_id']
