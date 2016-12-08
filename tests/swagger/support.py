
import unittest

from bravado_core.spec import Spec
from bravado_core.resource import build_resources
from bravado_core.response import OutgoingResponse

from ..support import (BaseWebTest, MINIMALIST_BUCKET, MINIMALIST_GROUP,
                       MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class SwaggerTest(BaseWebTest, unittest.TestCase):

    def __init__(self, *args, **kargs):
        super(SwaggerTest, self).__init__(*args, **kargs)

        self.spec_dict = self.app.get('/swagger.json').json
        self.spec = Spec.from_dict(self.spec_dict)
        self.resources = build_resources(self.spec)

    def setUp(self):
        super(SwaggerTest, self).setUp()

        self.bucket = self.app.put_json('/buckets/b1',
                                        MINIMALIST_BUCKET,
                                        headers=self.headers).json

        self.group = self.app.put_json('/buckets/b1/groups/g1',
                                       MINIMALIST_GROUP,
                                       headers=self.headers).json

        self.collection = self.app.put_json('/buckets/b1/collections/c1',
                                            MINIMALIST_COLLECTION,
                                            headers=self.headers).json

        self.record = self.app.put_json('/buckets/b1/collections/c1/records/r1',
                                        MINIMALIST_RECORD,
                                        headers=self.headers).json

    def cast_bravado_response(self, response):
        resp = OutgoingResponse()
        resp.text = response.body
        # XXX: empty response fails with Python 3
        # See https://github.com/Yelp/bravado-core/issues/134
        if not resp.text:
            resp.text = None
        resp.headers = response.headers
        # XXX: Drop charset (might be a bug on bravado)
        resp.content_type = response.headers.get('Content-Type', '').split(';')[0]
        resp.json = lambda: response.json

        return resp
