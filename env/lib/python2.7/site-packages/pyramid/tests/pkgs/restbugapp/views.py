from pyramid.response import Response

class BaseRESTView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
class PetRESTView(BaseRESTView):
    """ REST Controller to control action of an avatar """
    def __init__(self, context, request):
        super(PetRESTView, self).__init__(context, request)

    def GET(self):
        return Response('gotten')
    
