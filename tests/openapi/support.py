import unittest
import json

from bravado_core.spec import Spec
from bravado_core.resource import build_resources
from bravado_core.response import OutgoingResponse, validate_response
from bravado_core.request import IncomingRequest, unmarshal_request

from ..support import (
    BaseWebTest,
    MINIMALIST_BUCKET,
    MINIMALIST_GROUP,
    MINIMALIST_COLLECTION,
    MINIMALIST_RECORD,
)


class OpenAPITest(BaseWebTest, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec_dict = cls.app.get("/__api__").json
        bravado_config = {
            # use_models causes us to break in bravado-core 4.13.0,
            # probably because of
            # https://github.com/Yelp/bravado-core/pull/254, and we
            # don't actually use the generated models in our tests
            # here anyhow.
            "use_models": False
        }
        cls.spec = Spec.from_dict(cls.spec_dict, config=bravado_config)
        cls.resources = build_resources(cls.spec)

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings["includes"] = ["kinto.plugins.history", "kinto.plugins.admin"]
        return settings

    def setUp(self):
        super().setUp()

        self.bucket = self.app.put_json(
            "/buckets/b1", MINIMALIST_BUCKET, headers=self.headers
        ).json

        self.group = self.app.put_json(
            "/buckets/b1/groups/g1", MINIMALIST_GROUP, headers=self.headers
        ).json

        self.collection = self.app.put_json(
            "/buckets/b1/collections/c1", MINIMALIST_COLLECTION, headers=self.headers
        ).json

        self.record = self.app.put_json(
            "/buckets/b1/collections/c1/records/r1", MINIMALIST_RECORD, headers=self.headers
        ).json

        # Create raw Bravado request
        self.request = IncomingRequest()
        self.request.url = ""
        self.request.data = ""
        self.request.path = {}
        self.request.headers = {}
        self.request.query = {}
        self.request._json = {}
        self.request.json = lambda: self.request._json

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
        resp.content_type = response.headers.get("Content-Type", "").split(";")[0]
        resp.json = lambda: response.json

        return resp

    def validate_request_call(self, op, **kargs):
        params = unmarshal_request(self.request, op)
        response = self.app.request(
            op.path_name.format_map(params),
            body=json.dumps(self.request.json()).encode(),
            method=op.http_method.upper(),
            headers=self.headers,
            **kargs
        )
        schema = self.spec.deref(op.op_spec["responses"][str(response.status_code)])
        casted_resp = self.cast_bravado_response(response)
        validate_response(schema, op, casted_resp)
        return response
