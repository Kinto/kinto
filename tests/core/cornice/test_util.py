# -*- encoding: utf-8 -*-
import unittest
from unittest import mock

from kinto.core.cornice import util


class CurrentServiceTest(unittest.TestCase):
    def test_current_service_returns_the_service_for_existing_patterns(self):
        request = mock.MagicMock()
        request.matched_route.pattern = "/buckets"
        request.registry.cornice_services = {"/buckets": mock.sentinel.service}

        self.assertEqual(util.current_service(request), mock.sentinel.service)

    def test_current_service_returns_none_for_unexisting_patterns(self):
        request = mock.MagicMock()
        request.matched_route.pattern = "/unexisting"
        request.registry.cornice_services = {}

        self.assertEqual(util.current_service(request), None)
