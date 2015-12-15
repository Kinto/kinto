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

    def test_module_reload(self):
        directive = ServiceDirective(
            'test', [], {}, [], 1, 1, 'test', mock.Mock(), 1)
        directive.options['modules'] = ['cornice']
        directive.run()
        directive.run()
