from cornice import Service

batch = Service(name="batch", path='/batch',
                description="Batch operations")


@batch.post()
def post_batch(request):
    return {}
