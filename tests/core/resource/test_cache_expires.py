from . import BaseTest


class CacheExpires(BaseTest):
    setting = "test_cache_expires_seconds"

    def get_context(self):
        context = super().get_context()
        context.resource_name = "test"
        return context

    def get_request(self):
        request = super().get_request()
        request.prefixed_userid = None  # Anonymous.
        return request

    def test_no_cache_expires_by_default(self):
        settings = self.resource.request.registry.settings
        settings.pop(self.setting, None)
        self.resource.plural_get()
        self.assertFalse(self.last_response.cache_expires.called)

    def test_cache_expires_using_setting_with_resource_name(self):
        settings = self.resource.request.registry.settings
        settings[self.setting] = 3
        self.resource.plural_get()
        self.last_response.cache_expires.assert_called_with(seconds=3)

    def test_cache_expires_is_also_on_object_get(self):
        stored = self.model.create_object({})
        self.resource.object_id = stored["id"]
        settings = self.resource.request.registry.settings
        settings[self.setting] = 3
        self.resource.get()
        self.last_response.cache_expires.assert_called_with(seconds=3)

    def test_cache_expires_even_if_zero(self):
        settings = self.resource.request.registry.settings
        settings[self.setting] = 0
        self.resource.plural_get()
        self.assertTrue(self.last_response.cache_control.no_cache)
