from .support import BaseWebTest, unittest


MINIMALIST_ITEM = dict(members=['fxa:user'])


class GroupViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/groups'
    record_url = '/buckets/beers/groups/moderators'

    def test_groups_can_be_posted_without_id(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_ITEM,
                                  headers=self.headers,
                                  status=201)
        self.assertIn('id', resp.json)
        self.assertEqual(resp.json['members'], ['fxa:user'])

    def test_groups_can_be_put_with_simple_name(self):
        response = self.app.put_json(self.record_url,
                                     MINIMALIST_ITEM,
                                     headers=self.headers)
        self.assertEqual(response.json['id'], 'moderators')

    def test_groups_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/groups/__moderator__',
                          MINIMALIST_ITEM,
                          headers=self.headers,
                          status=400)

    def test_groups_are_isolated_by_bucket(self):
        self.app.put_json(self.record_url,
                          MINIMALIST_ITEM,
                          headers=self.headers)
        other_bucket = self.record_url.replace('beers', 'water')
        self.app.get(other_bucket, headers=self.headers, status=404)

    def test_groups_creation_fails_if_bucket_is_not_found(self):
        pass


class GroupDeletionTest(BaseWebTest, unittest.TestCase):

    record_url = '/buckets/beers/groups/moderators'

    def test_groups_can_be_deleted(self):
        self.app.put_json(self.record_url, MINIMALIST_ITEM,
                          headers=self.headers)
        self.app.delete(self.record_url, headers=self.headers)
        self.app.get(self.record_url, headers=self.headers,
                     status=404)

    def test_principal_is_removed_from_users_when_group_deleted(self):
        pass


class InvalidGroupTest(BaseWebTest, unittest.TestCase):

    record_url = '/buckets/beers/groups/moderators'

    def test_groups_must_have_members_attribute(self):
        invalid = {}
        self.app.put_json(self.record_url,
                          invalid,
                          headers=self.headers,
                          status=400)


class GroupPrincipalsTest(BaseWebTest, unittest.TestCase):

    def test_principal_is_added_to_user_when_added_to_members(self):
        pass

    def test_principal_is_removed_from_user_when_removed_from_members(self):
        pass
