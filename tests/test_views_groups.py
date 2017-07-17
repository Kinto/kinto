import unittest
from kinto.core.errors import ERRORS
from kinto.core.testing import FormattedErrorMixin

from .support import (BaseWebTest, MINIMALIST_BUCKET,
                      MINIMALIST_GROUP)


class GroupViewTest(FormattedErrorMixin, BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/groups'
    record_url = '/buckets/beers/groups/moderators'

    def setUp(self):
        super().setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        resp = self.app.put_json(self.record_url,
                                 MINIMALIST_GROUP,
                                 headers=self.headers)
        self.record = resp.json['data']

    def test_collection_endpoint_lists_them_all(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['members'], ['fxa:user'])

    def test_groups_can_be_posted_without_id(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_GROUP,
                                  headers=self.headers,
                                  status=201)
        self.assertIn('id', resp.json['data'])
        self.assertEqual(resp.json['data']['members'], ['fxa:user'])

    def test_groups_can_be_put_with_empty_body(self):
        self.app.put('/buckets/beers/groups/simple', headers=self.headers)

    def test_groups_can_be_created_with_just_permissions(self):
        group = {'permissions': {'write': ['github:me']}}
        resp = self.app.put_json('/buckets/beers/groups/g',
                                 group,
                                 headers=self.headers)
        self.assertNotIn('members', resp.json['data'])

    def test_groups_can_be_create_without_members_attribute(self):
        group = {'data': {'alias': 'admins'}}
        resp = self.app.put_json(self.record_url,
                                 group,
                                 headers=self.headers)
        self.assertEqual(resp.json['data']['members'], [])

    def test_groups_can_be_patched_without_members_attribute(self):
        group = {'data': {'alias': 'admins'}}
        resp = self.app.patch_json(self.record_url,
                                   group,
                                   headers=self.headers)
        self.assertEqual(resp.json['data']['members'], ['fxa:user'])
        self.assertEqual(resp.json['data']['alias'], 'admins')

    def test_groups_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'moderators')

    def test_groups_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/groups/__moderator__',
                          MINIMALIST_GROUP,
                          headers=self.headers,
                          status=400)

    def test_groups_can_have_arbitrary_attributes(self):
        mailinglist = "kinto@mozilla.com"
        group = {**MINIMALIST_GROUP, 'data': {**MINIMALIST_GROUP['data'],
                                              'mailinglist': mailinglist}}
        resp = self.app.put_json('/buckets/beers/groups/moderator',
                                 group,
                                 headers=self.headers)
        data = resp.json['data']
        self.assertIn('mailinglist', data)
        self.assertEqual(data['mailinglist'], mailinglist)

    def test_groups_can_be_filtered_by_arbitrary_attribute(self):
        group = {**MINIMALIST_GROUP, 'data': {**MINIMALIST_GROUP['data'], 'size': 3}}
        self.app.put_json('/buckets/beers/groups/moderator',
                          group,
                          headers=self.headers)
        resp = self.app.get('/buckets/beers/groups?has_size=true&min_size=2',
                            headers=self.headers)
        data = resp.json['data']
        self.assertEqual(len(data), 1)

    def test_groups_should_reject_unaccepted_request_content_type(self):
        headers = {**self.headers, 'Content-Type': 'text/plain'}
        self.app.put('/buckets/beers/groups/moderator',
                     MINIMALIST_GROUP,
                     headers=headers,
                     status=415)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_groups_are_isolated_by_bucket(self):
        other_bucket = self.record_url.replace('beers', 'sodas')
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(other_bucket, headers=self.headers, status=404)

    def test_wrong_create_permissions_cannot_be_added_on_groups(self):
        group = {**MINIMALIST_GROUP, 'permissions': {'group:create': ['fxa:user']}}
        self.app.put_json('/buckets/beers/groups/moderator',
                          group,
                          headers=self.headers,
                          status=400)

    def test_recreate_group_after_deletion_returns_a_201(self):
        self.app.put_json('/buckets/beers/groups/moderator',
                          MINIMALIST_GROUP,
                          headers=self.headers,
                          status=201)
        self.app.delete('/buckets/beers/groups/moderator',
                        headers=self.headers,
                        status=200)
        self.app.put_json('/buckets/beers/groups/moderator',
                          MINIMALIST_GROUP,
                          headers=self.headers,
                          status=201)

    def test_group_doesnt_accept_system_Everyone(self):
        group = {**MINIMALIST_GROUP, 'data': {'members': ['system.Everyone']}}
        response = self.app.put_json('/buckets/beers/groups/moderator',
                                     group,
                                     headers=self.headers,
                                     status=400)
        self.assertFormattedError(
            response, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters",
            "'system.Everyone' is not a valid user ID.")

    def test_group_doesnt_accept_groups_inside_groups(self):
        group = {**MINIMALIST_GROUP, 'data': {'members': ['/buckets/beers/groups/administrators']}}
        response = self.app.put_json('/buckets/beers/groups/moderator',
                                     group,
                                     headers=self.headers,
                                     status=400)
        self.assertFormattedError(
            response, 400, ERRORS.INVALID_PARAMETERS,
            "Invalid parameters",
            "'/buckets/beers/groups/administrators' is not a valid user ID.")


class GroupManagementTest(BaseWebTest, unittest.TestCase):

    group_url = '/buckets/beers/groups/moderators'

    def setUp(self):
        super().setUp()
        self.create_bucket('beers')

    def test_groups_can_be_deleted(self):
        self.create_group('beers', 'moderators')
        self.app.delete(self.group_url, headers=self.headers)
        self.app.get(self.group_url, headers=self.headers,
                     status=404)

    def test_unknown_group_raises_404(self):
        other_group = self.group_url.replace('moderators', 'blah')
        resp = self.app.get(other_group, headers=self.headers, status=404)
        self.assertEqual(resp.json['details']['id'], 'blah')
        self.assertEqual(resp.json['details']['resource_name'], 'group')

    def test_group_is_removed_from_users_principals_on_group_deletion(self):
        self.app.put_json(self.group_url, MINIMALIST_GROUP,
                          headers=self.headers, status=201)
        self.assertIn(self.group_url,
                      self.permission.get_user_principals('fxa:user'))
        self.app.delete(self.group_url, headers=self.headers, status=200)
        self.assertNotIn(self.group_url,
                         self.permission.get_user_principals('fxa:user'))

    def test_group_is_removed_from_users_principals_on_groups_deletion(self):
        self.create_group('beers', 'moderators', ['natim', 'fxa:me'])
        self.create_group('beers', 'reviewers', ['natim', 'alexis'])

        self.app.delete('/buckets/beers/groups', headers=self.headers,
                        status=200)

        self.assertEquals(self.permission.get_user_principals('fxa:me'), set())
        self.assertEquals(self.permission.get_user_principals('natim'), set())
        self.assertEquals(self.permission.get_user_principals('alexis'), set())

    def test_group_is_added_to_user_principals_when_added_to_members(self):
        self.create_group('beers', 'moderators', ['natim', 'mat'])

        self.app.get('/buckets/beers/groups', headers=self.headers, status=200)
        self.assertEquals(self.permission.get_user_principals('natim'),
                          {'/buckets/beers/groups/moderators'})
        self.assertEquals(self.permission.get_user_principals('mat'),
                          {'/buckets/beers/groups/moderators'})

    def test_group_is_added_to_user_principals_on_members_add_with_patch(self):
        self.create_group('beers', 'moderators', ['natim', 'mat'])
        group_url = '/buckets/beers/groups/moderators'
        group = {'data': {'members': ['natim', 'mat', 'alice']}}
        self.app.patch_json(group_url, group,
                            headers=self.headers, status=200)
        self.app.get('/buckets/beers/groups', headers=self.headers, status=200)
        self.assertEquals(self.permission.get_user_principals('natim'),
                          {group_url})
        self.assertEquals(self.permission.get_user_principals('mat'),
                          {group_url})
        self.assertEquals(self.permission.get_user_principals('alice'),
                          {group_url})

    def test_group_member_removal_updates_user_principals(self):
        self.create_group('beers', 'moderators', ['natim', 'mat'])
        group_url = '/buckets/beers/groups/moderators'
        group = {'data': {'members': ['mat']}}
        self.app.put_json(group_url, group,
                          headers=self.headers, status=200)
        self.app.get('/buckets/beers/groups', headers=self.headers, status=200)
        self.assertEquals(self.permission.get_user_principals('natim'), set())
        self.assertEquals(self.permission.get_user_principals('mat'),
                          {group_url})

    def test_group_with_authenticated_is_added_to_everbody(self):
        self.create_group('beers', 'reviewers', ['system.Authenticated'])
        self.assertEquals(self.permission.get_user_principals('natim'),
                          {'/buckets/beers/groups/reviewers'})
        self.assertEquals(self.permission.get_user_principals('mat'),
                          {'/buckets/beers/groups/reviewers'})

    def test_group_member_removal_updates_user_principals_with_patch(self):
        self.create_group('beers', 'moderators', ['natim', 'mat'])
        group_url = '/buckets/beers/groups/moderators'
        group = {'data': {'members': ['mat']}}
        self.app.patch_json(group_url, group, headers=self.headers, status=200)
        self.assertEquals(self.permission.get_user_principals('natim'), set())
        self.assertEquals(self.permission.get_user_principals('mat'),
                          {group_url})

    def test_groups_can_be_created_after_deletion(self):
        self.create_group('beers', 'moderators')
        group_url = '/buckets/beers/groups/moderators'
        self.app.delete(group_url, headers=self.headers)
        headers = {**self.headers, 'If-None-Match': '*'}
        self.app.put_json(group_url, MINIMALIST_GROUP,
                          headers=headers, status=201)

    def test_groups_data_is_optional_with_patch(self):
        valid = {'permissions': {'write': ['github:me']}}
        self.app.put_json(self.group_url, MINIMALIST_GROUP,
                          headers=self.headers)
        self.app.patch_json(self.group_url,
                            valid,
                            headers=self.headers)
