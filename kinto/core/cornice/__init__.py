# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from pyramid.events import NewRequest

from kinto.core.cornice.errors import Errors  # NOQA
from kinto.core.cornice.pyramidhook import (
    register_service_views,
    wrap_request,
)
from kinto.core.cornice.renderer import CorniceRenderer
from kinto.core.cornice.service import Service  # NOQA
from kinto.core.cornice.util import ContentTypePredicate, current_service


logger = logging.getLogger("kinto.core.cornice")


def includeme(config):
    """Include the Cornice definitions"""
    # attributes required to maintain services
    config.registry.cornice_services = {}

    config.add_directive("add_cornice_service", register_service_views)
    config.add_subscriber(wrap_request, NewRequest)
    config.add_renderer("cornicejson", CorniceRenderer())
    config.add_view_predicate("content_type", ContentTypePredicate)
    config.add_request_method(current_service, reify=True)
