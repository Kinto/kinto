# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import json
from rxjson import Rx
from cornice.tests.support import TestCase
from cornice.service import Service, get_services
from cornice.ext.spore import generate_spore_description

HERE = os.path.dirname(os.path.abspath(__file__))


class TestSporeGeneration(TestCase):

    def _define_coffee_methods(self, service):
        @service.get()
        def get_coffee(request):
            pass

    def test_generate_spore_description(self):

        coffees = Service(name='Coffees', path='/coffee')
        coffee = Service(name='coffee', path='/coffee/{bar}/{id}')

        @coffees.post()
        def post_coffees(request):
            """Post information about the coffee"""
            return "ok"

        self._define_coffee_methods(coffee)
        self._define_coffee_methods(coffees)

        services = get_services(names=('coffee', 'Coffees'))
        spore = generate_spore_description(
            services, name="oh yeah",
            base_url="http://localhost/", version="1.0")

        # basic fields
        self.assertEqual(spore['name'], "oh yeah")
        self.assertEqual(spore['base_url'], "http://localhost/")
        self.assertEqual(spore['version'], "1.0")

        # methods
        methods = spore['methods']
        self.assertIn('get_coffees', methods)
        self.assertDictEqual(methods['get_coffees'], {
            'path': '/coffee',
            'method': 'GET',
            'formats': ['json'],
        })

        self.assertIn('post_coffees', methods)
        self.assertDictEqual(methods['post_coffees'], {
            'path': '/coffee',
            'method': 'POST',
            'formats': ['json'],
            'description': post_coffees.__doc__
        })

        self.assertIn('get_coffee', methods)
        self.assertDictEqual(methods['get_coffee'], {
            'path': '/coffee/:bar/:id',
            'method': 'GET',
            'formats': ['json'],
            'required_params': ['bar', 'id']
        })

    def test_rxjson_spore(self):
        rx = Rx.Factory({'register_core_types': True})

        coffees = Service(name='Coffees', path='/coffee')
        coffee = Service(name='coffee', path='/coffee/{bar}/{id}')

        self._define_coffee_methods(coffee)
        self._define_coffee_methods(coffees)

        services = get_services(names=('coffee', 'Coffees'))
        spore = generate_spore_description(
            services, name="oh yeah",
            base_url="http://localhost/", version="1.0")

        with open(os.path.join(HERE, 'spore_validation.rx')) as f:
            spore_json_schema = json.loads(f.read())
            spore_schema = rx.make_schema(spore_json_schema)
            self.assertTrue(spore_schema.check(spore))
