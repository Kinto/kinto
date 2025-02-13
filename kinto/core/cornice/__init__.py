# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from functools import partial

from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.settings import asbool, aslist

from kinto.core.cornice.errors import Errors  # NOQA
from kinto.core.cornice.pyramidhook import (
    handle_exceptions,
    register_resource_views,
    register_service_views,
    wrap_request,
)
from kinto.core.cornice.renderer import CorniceRenderer
from kinto.core.cornice.service import Service  # NOQA
from kinto.core.cornice.util import ContentTypePredicate, current_service


logger = logging.getLogger("cornice")


def set_localizer_for_languages(event, available_languages, default_locale_name):
    """
    Sets the current locale based on the incoming Accept-Language header, if
    present, and sets a localizer attribute on the request object based on
    the current locale.

    To be used as an event handler, this function needs to be partially applied
    with the available_languages and default_locale_name arguments. The
    resulting function will be an event handler which takes an event object as
    its only argument.
    """
    request = event.request
    if request.accept_language:
        accepted = request.accept_language.lookup(available_languages, default=default_locale_name)
        request._LOCALE_ = accepted


def setup_localization(config):
    """
    Setup localization based on the available_languages and
    pyramid.default_locale_name settings.

    These settings are named after suggestions from the "Internationalization
    and Localization" section of the Pyramid documentation.
    """
    try:
        config.add_translation_dirs("colander:locale/")
        settings = config.get_settings()
        available_languages = aslist(settings["available_languages"])
        default_locale_name = settings.get("pyramid.default_locale_name", "en")
        set_localizer = partial(
            set_localizer_for_languages,
            available_languages=available_languages,
            default_locale_name=default_locale_name,
        )
        config.add_subscriber(set_localizer, NewRequest)
    except ImportError:  # pragma: no cover
        # add_translation_dirs raises an ImportError if colander is not
        # installed
        pass


def includeme(config):
    """Include the Cornice definitions"""
    # attributes required to maintain services
    config.registry.cornice_services = {}

    settings = config.get_settings()

    # localization request subscriber must be set before first call
    # for request.localizer (in wrap_request)
    if settings.get("available_languages"):
        setup_localization(config)

    config.add_directive("add_cornice_service", register_service_views)
    config.add_directive("add_cornice_resource", register_resource_views)
    config.add_subscriber(wrap_request, NewRequest)
    config.add_renderer("cornicejson", CorniceRenderer())
    config.add_view_predicate("content_type", ContentTypePredicate)
    config.add_request_method(current_service, reify=True)

    if asbool(settings.get("handle_exceptions", True)):
        config.add_view(handle_exceptions, context=Exception, permission=NO_PERMISSION_REQUIRED)
        config.add_view(handle_exceptions, context=HTTPNotFound, permission=NO_PERMISSION_REQUIRED)
        config.add_view(
            handle_exceptions, context=HTTPForbidden, permission=NO_PERMISSION_REQUIRED
        )
