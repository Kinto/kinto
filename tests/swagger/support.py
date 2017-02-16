import unittest
import json

from bravado_core.spec import Spec
from bravado_core.resource import build_resources
from bravado_core.response import OutgoingResponse, validate_response
from bravado_core.request import IncomingRequest, unmarshal_request

from ..support import (BaseWebTest, MINIMALIST_BUCKET, MINIMALIST_GROUP,
                       MINIMALIST_COLLECTION, MINIMALIST_RECORD)


class SwaggerTest(BaseWebTest, unittest.TestCase):

    settings = {
        'includes': [
            'kinto.plugins.history',
            'kinto.plugins.admin',
        ]
    }

    @classmethod
    def setUpClass(cls):
        # FIXME: solve memory issues from generating the spec multiple times
        app = BaseWebTest().make_app(settings=cls.settings)

        cls.spec_dict = app.get('/__api__').json
        cls.spec = Spec.from_dict(cls.spec_dict)
        cls.resources = build_resources(cls.spec)

    def setUp(self):
        super().setUp()

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

        # Create raw Bravado request
        self.request = IncomingRequest()
        self.request.url = ''
        self.request.data = ''
        self.request.path = {}
        self.request.headers = {}
        self.request.query = {}
        self.request._json = {}
        self.request.json = lambda: self.request._json

    def get_app_settings(self, extras=None):
        settings = super().get_app_settings(extras)
        settings.update(self.settings)
        return settings

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

    def validate_request_call(self, op, **kargs):
        params = unmarshal_request(self.request, op)
        response = self.app.request(op.path_name.format_map(params),
                                    body=json.dumps(self.request.json()).encode(),
                                    method=op.http_method.upper(),
                                    headers=self.headers, **kargs)
        schema = self.spec.deref(op.op_spec['responses'][str(response.status_code)])
        casted_resp = self.cast_bravado_response(response)
        validate_response(schema, op, casted_resp)
        return response
