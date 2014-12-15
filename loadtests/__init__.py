from requests.auth import HTTPBasicAuth
from loads.case import TestCase


class TestPOC(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPOC, self).__init__(*args, **kwargs)

        self.alice_auth = HTTPBasicAuth('alice', 'secret')
        self.john_auth = HTTPBasicAuth('john', 'secret')

    def api_url(self, path):
        return "{0}/v1/{1}".format(self.server_url, path)

    def test_all(self):
        self.test_home()
        self.test_create_record()
        self.test_update_status()
        self.test_list_filtered()

    def test_home(self):
        res = self.session.get(self.api_url('article'), auth=self.alice_auth)
        self.assertEqual(res.status_code, 200)

    def test_create_record(self):
        data = {
            "title": "Corp Site",
            "url": "http://mozilla.org",
            "status": "unread"
        }
        res = self.session.post(
            self.api_url('article'),
            data,
            auth=self.alice_auth)
        self.assertEqual(res.status_code, 201)

    def test_update_status(self):
        res = self.session.get(self.api_url('article'), auth=self.alice_auth)
        record = res.json()['_items'][0]

        data = {'status': 'read'}
        headers = {"If-Match": record['_etag']}

        res = self.session.patch(
            self.api_url('article/%s' % record['_id']),
            data,
            auth=self.alice_auth,
            headers=headers
            )
        self.assertEqual(res.status_code, 200)

    def test_list_filtered(self):
        res = self.session.get(self.api_url('article'), auth=self.john_auth)
        self.assertEqual(len(res.json()['_items']), 0)
