import unittest

from bravado_core.spec import Spec
from bravado_core.resource import build_resources
from bravado_core.response import OutgoingResponse

from ..support import (BaseWebTest, MINIMALIST_BUCKET, MINIMALIST_GROUP,
                       MINIMALIST_COLLECTION, MINIMALIST_RECORD)


app = BaseWebTest().make_app()

spec_dict = app.get('/swagger.json').json
spec = Spec.from_dict(spec_dict)
resources = build_resources(spec)


class SwaggerTest(BaseWebTest, unittest.TestCase):

    def setUp(self):

        # FIXME: solve memory issues from generating the spec multiple times
        self.spec_dict = spec_dict
        self.spec = spec
        self.resources = resources

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

        # FIXME: Empty response fails with Bravado and Python 3
        # See https://github.com/Yelp/bravado-core/issues/134
        if not resp.text:
            resp.text = None

        resp.headers = response.headers
        # Response headers integer fields are not casted by default
        for k, v in resp.headers.items():
            try:
                resp.headers[k] = int(v)
            except ValueError:
                pass

        # FIXME: Drop charset from application/json response on Pyramid
        # See https://github.com/Pylons/pyramid/issues/2860
        resp.content_type = response.headers.get('Content-Type', '').split(';')[0]
        resp.json = lambda: response.json

        return resp
