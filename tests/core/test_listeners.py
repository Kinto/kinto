import os
import uuid
from unittest import mock

from pyramid import testing

from kinto.core import initialization
from kinto.core.events import ResourceChanged, ResourceRead, ACTIONS
from kinto.core.listeners import ListenerBase
from kinto.core.testing import unittest


UID = str(uuid.uuid4())


class ViewSet:
    def get_name(*args, **kw):
        return "mushrooms"


class Service:
    viewset = ViewSet()


class Match:
    cornice_services = {"watev": Service()}
    pattern = "watev"


class Request:
    path = "/1/school/students/"
    prefixed_userid = "tarek"
    matchdict = {"id": UID}
    registry = matched_route = Match()
    current_resource_name = "school"


class ListenerSetupTest(unittest.TestCase):
    def setUp(self):
        demo_patch = mock.patch("tests.core.listeners.load_from_config")
        self.addCleanup(demo_patch.stop)
        self.demo_mocked = demo_patch.start()

    def make_app(self, extra_settings={}):
        settings = {"event_listeners": "tests.core.listeners"}
        settings.update(**extra_settings)
        config = testing.setUp(settings=settings)
        config.commit()
        initialization.setup_listeners(config)
        return config

    def test_listener_module_is_specified_via_settings(self):
        self.make_app(
            {"event_listeners": "demo", "event_listeners.demo.use": "tests.core.listeners"}
        )
        self.assertTrue(self.demo_mocked.called)

    def test_listener_module_can_be_specified_via_listeners_list(self):
        self.make_app(
            {"event_listeners": "demo", "event_listeners.demo.use": "tests.core.listeners"}
        )
        self.assertTrue(self.demo_mocked.called)

    def test_callback_called_when_action_is_not_filtered(self):
        config = self.make_app(
            {"event_listeners": "demo", "event_listeners.demo.use": "tests.core.listeners"}
        )
        ev = ResourceChanged({"action": ACTIONS.CREATE.value}, [], Request())
        config.registry.notify(ev)

        self.assertTrue(self.demo_mocked.return_value.called)

    def test_callback_is_not_called_when_action_is_filtered(self):
        config = self.make_app(
            {
                "event_listeners": "demo",
                "event_listeners.demo.use": "tests.core.listeners",
                "event_listeners.demo.actions": "delete",
            }
        )
        ev = ResourceChanged({"action": ACTIONS.CREATE.value}, [], Request())
        config.registry.notify(ev)

        self.assertFalse(self.demo_mocked.return_value.called)

    def test_callback_called_when_resource_is_not_filtered(self):
        config = self.make_app(
            {"event_listeners": "demo", "event_listeners.demo.use": "tests.core.listeners"}
        )
        event = ResourceChanged(
            {"action": ACTIONS.CREATE.value, "resource_name": "mushroom"}, [], Request()
        )
        config.registry.notify(event)

        self.assertTrue(self.demo_mocked.return_value.called)

    def test_callback_is_not_called_when_resource_is_filtered(self):
        config = self.make_app(
            {
                "event_listeners": "demo",
                "event_listeners.demo.use": "tests.core.listeners",
                "event_listeners.demo.resources": "toad",
            }
        )
        event = ResourceChanged(
            {"action": ACTIONS.CREATE.value, "resource_name": "mushroom"}, [], Request()
        )
        config.registry.notify(event)

        self.assertFalse(self.demo_mocked.return_value.called)

    def test_callback_is_not_called_on_read_by_default(self):
        config = self.make_app(
            {"event_listeners": "demo", "event_listeners.demo.use": "tests.core.listeners"}
        )
        event = ResourceRead({"action": ACTIONS.READ.value}, [], Request())
        config.registry.notify(event)

        self.assertFalse(self.demo_mocked.return_value.called)

    def test_callback_is_called_on_read_if_specified(self):
        config = self.make_app(
            {
                "event_listeners": "demo",
                "event_listeners.demo.use": "tests.core.listeners",
                "event_listeners.demo.actions": "read",
            }
        )
        event = ResourceRead({"action": ACTIONS.READ.value}, [], Request())
        config.registry.notify(event)

        self.assertTrue(self.demo_mocked.return_value.called)

    def test_same_callback_is_called_for_read_and_write_specified(self):
        config = self.make_app(
            {
                "event_listeners": "demo",
                "event_listeners.demo.use": "tests.core.listeners",
                "event_listeners.demo.actions": "read create delete",
            }
        )
        ev = ResourceRead({"action": ACTIONS.READ.value}, [], Request())
        config.registry.notify(ev)
        ev = ResourceChanged({"action": ACTIONS.CREATE.value}, [], Request())
        config.registry.notify(ev)

        self.assertEqual(self.demo_mocked.return_value.call_count, 2)

    def test_loading_can_read_configuration_from_environment(self):
        environ = {
            "KINTO_EVENT_LISTENERS": "kvstore",
            "KINTO_EVENT_LISTENERS_KVSTORE_USE": "tests.core.listeners",
            "KINTO_EVENT_LISTENERS_KVSTORE_URL": "demo://demo:6379/0",
            "KINTO_EVENT_LISTENERS_KVSTORE_POOL_SIZE": "5",
            "KINTO_EVENT_LISTENERS_KVSTORE_LISTNAME": "queue",
            "KINTO_EVENT_LISTENERS_KVSTORE_ACTIONS": "delete",
            "KINTO_EVENT_LISTENERS_KVSTORE_RESOURCES": "toad",
        }
        os.environ.update(**environ)

        config = self.make_app(
            {
                # With real/full initialization, these should not be necessary:
                "settings_prefix": "kinto",
                "event_listeners": "kvstore",
            }
        )

        # Listener is instantiated.
        self.assertTrue(self.demo_mocked.called)

        # Action filtering is read from ENV.
        event = ResourceChanged(
            {"action": ACTIONS.DELETE.value, "resource_name": "toad"}, [], Request()
        )
        config.registry.notify(event)
        self.assertTrue(self.demo_mocked.return_value.called)

        self.demo_mocked.reset_mock()

        # Action filtering is read from ENV.
        event = ResourceChanged({"action": ACTIONS.CREATE.value}, [], Request())
        config.registry.notify(event)
        self.assertFalse(self.demo_mocked.return_value.called)

        # Resource filtering is read from ENV.
        event = ResourceChanged(
            {"action": ACTIONS.CREATE.value, "resource_name": "mushroom"}, [], Request()
        )
        config.registry.notify(event)
        self.assertFalse(self.demo_mocked.return_value.called)

        # Clean-up.
        for k in environ.keys():
            os.environ.pop(k)


class ListenerBaseTest(unittest.TestCase):
    def test_not_implemented(self):
        # make sure we can't use the base listener
        listener = ListenerBase()
        self.assertRaises(NotImplementedError, listener, object())
