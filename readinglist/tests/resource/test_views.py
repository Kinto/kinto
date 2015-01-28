# class ResourceAuthorizationTest():
#     @mock.patch('readinglist.authentication.AuthorizationPolicy.permits')
#     def test_view_permissions(self, permits_mocked):
#         permission_required = lambda: permits_mocked.call_args[0][-1]

#         self.app.get(self.collection_url)
#         self.assertEqual(permission_required(), 'readonly')

#         resp = self.app.post_json(self.collection_url,
#                                   self.record_factory())
#         self.assertEqual(permission_required(), 'readwrite')

#         url = self.item_url.format(id=resp.json['_id'])
#         self.app.get(url)
#         self.assertEqual(permission_required(), 'readonly')

#         self.app.patch_json(url, {})
#         self.assertEqual(permission_required(), 'readwrite')

#         self.app.delete(url)
#         self.assertEqual(permission_required(), 'readwrite')

# def test_all_views_require_authentication(self):
#     record = self.record_factory()
#     self.app.get(self.collection_url, status=401)
#     self.app.post(self.collection_url, record, status=401)
#     url = self.item_url.format(id='abc')
#     self.app.get(url, status=401)
#     self.app.patch(url, record, status=401)
#     self.app.delete(url, status=401)

# class InvalidRecordTest(BaseTest):
#     def test_invalid_record_raises_error(self):
#         body = self.invalid_record_factory()
#         resp = self.app.post_json(self.collection_url,
#                                   body,
#                                   headers=self.headers,
#                                   status=400)
#         self.assertFormattedError(
#             resp, 400, ERRORS.INVALID_PARAMETERS,
#             "Invalid parameters", "is missing")

#     def test_modify_with_invalid_record(self):
#         url = self.item_url.format(id=self.record['_id'])
#         stored = self.db.get(self.resource, u'bob', self.record['_id'])
#         for k in self._get_modified_keys():
#             stored.pop(k)
#         resp = self.app.patch_json(url,
#                                    stored,
#                                    headers=self.headers,
#                                    status=400)
#         self.assertFormattedError(
#             resp, 400, ERRORS.INVALID_PARAMETERS,
#             "Invalid parameters", "Required")

#     def test_replace_with_invalid_record(self):
#         url = self.item_url.format(id=self.record['_id'])
#         body = self.invalid_record_factory()
#         resp = self.app.put_json(url, body, headers=self.headers, status=400)
#         self.assertFormattedError(
#             resp, 400, ERRORS.INVALID_PARAMETERS,
#             "Invalid parameters", "is missing")


# class InvalidJSONTest(BaseTest):
#     def setUp(self):
#         super(InvalidJSONTest, self).setUp()
#         class FailingJSON(mock.MagicMock):
#             def __getattr__(self, name):
#                 if name == 'json':
#                     raise ValueError
#                 return super(FailingJSON, self).__getattr__(name)
#         self.resource.request = FailingJSON()
#         stored = self.db.create(self.resource, 'bob', {})
#         self.resource.request.matchdict['id'] = stored['_id']

#     def test_modify_with_invalid_json(self):
#         #"{'foo>}"
#         resp = self.resource.patch()
#         print resp
#         # self.assertFormattedError(
#         #     resp, 400, ERRORS.INVALID_PARAMETERS,
#         #     "Invalid parameters", "Invalid JSON request body")

# def test_empty_body_raises_error(self):
#     self.resource.request.content = ''
#     self.resource.collection_post()
#     print self.resource.request.errors
#     # self.assertFormattedError(
#     #     self.res, 400, ERRORS.INVALID_PARAMETERS,
#     #     "Invalid parameters", "is missing")

# def test_create_with_invalid_json(self):
#     body = "{'foo>}"
#     resp = self.app.post(self.collection_url,
#                          body,
#                          headers=self.headers,
#                          status=400)
#     self.assertFormattedError(
#         resp, 400, ERRORS.INVALID_PARAMETERS,
#         "Invalid parameters", "Invalid JSON request body")

# def test_invalid_uft8_raises_error(self):
#     body = '{"foo": "\\u0d1"}'
#     resp = self.app.post(self.collection_url,
#                          body,
#                          headers=self.headers,
#                          status=400)
#     self.assertFormattedError(
#         resp, 400, ERRORS.INVALID_PARAMETERS,
#         "Invalid parameters",
#         "body: Invalid JSON request body: Invalid \\uXXXX escape sequence:"
#         " line 1 column 11 (char 10)")

# def test_replace_with_invalid_json(self):
#     url = self.item_url.format(id=self.record['_id'])
#     body = "{'foo>}"
#     resp = self.app.put(url, body, headers=self.headers, status=400)
#     self.assertFormattedError(
#         resp, 400, ERRORS.INVALID_PARAMETERS,
#         "Invalid parameters", "Invalid JSON request body")
