import unittest
import six

from bravado_core.response import validate_response
from bravado_core.param import marshal_param

from .support import SwaggerTest


class MetaResourcesTest(type):
    """Metaprogram test cases for easy debugging."""

    def __init__(cls, *args, **kargs):
        unittest.case.TestCase = cls
        cls.generate_test_resources()

    def generate_test_resources(cls):
        for resource in cls.resources.values():
            for op_id, op in resource.operations.items():
                if op_id not in cls.allowed_failures:
                    setattr(cls, 'test_resource_%s' % op_id,
                            lambda self: cls.validate_request_call(self, op))


class SwaggerResourcesTest(six.with_metaclass(MetaResourcesTest, SwaggerTest)):

    allowed_failures = ['version']

    def validate_request_call(self, op, **kargs):

        self.request.url = op.path_name

        request = self.request.__dict__
        for param_id, param in op.params.items():
            marshal_param(param, self.params.get(param_id), request)

        response = self.app.request(request['url'],
                                    body=request['data'].encode(),
                                    method=op.http_method.upper(),
                                    headers=self.headers, **kargs)

        schema = self.spec.deref(op.op_spec['responses'][str(response.status_code)])
        casted_resp = self.cast_bravado_response(response)
        validate_response(schema, op, casted_resp)
        return response
