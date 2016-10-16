# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import mock

from cornice.tests.support import TestCase
from cornice.ext.sphinxext import rst2html, ServiceDirective


class TestUtil(TestCase):

    def test_rendering(self):
        text = '**simple render**'
        res = rst2html(text)
        self.assertEqual(res, b'<p><strong>simple render</strong></p>')
        self.assertEqual(rst2html(''), '')


class TestServiceDirective(TestCase):

    def setUp(self):
        super(TestServiceDirective, self).setUp()
        param = mock.Mock()
        param.document.settings.env.new_serialno.return_value = 1

        self.directive = ServiceDirective(
            'test', [], {}, [], 1, 1, 'test', param, 1)
        self.directive.options['app'] = 'cornice.tests.ext.dummy'
        self.directive.options['services'] = ['users', "thing_service"]

    def test_module_reload(self):
        self.directive.options['app'] = None
        self.directive.options['services'] = None
        self.directive.options['modules'] = ['cornice']
        ret = self.directive.run()
        self.assertEqual(ret, [])

    def test_dummy(self):
        ret = self.directive.run()
        self.assertEqual(len(ret), 2)
        self.assertIn('Users service at', str(ret[0]))
        self.assertIn('Thing_Service service at ', str(ret[1]))

    def test_string_validator_resolved(self):
        # A validator defined as a string should be parsed as an obj,
        # ensuring the docstring contains validator.__doc__ rather
        # than str.__doc__.
        ret = self.directive.run()
        self.assertNotIn("str(object='') -> string", str(ret[0]))
