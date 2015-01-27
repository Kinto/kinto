import json
import random
import uuid

from requests.auth import HTTPBasicAuth
from loads.case import TestCase


ACTIONS_FREQUENCIES = [
    ('create', 20),
    ('update', 50),
    ('filter_sort', 60),
    ('read_further', 80),
    ('mark_as_read', 40),
    ('create_conflict', 10),
    ('update_conflict', 10),
    ('archive', 10),
    ('delete', 10)
]


class TestBasic(TestCase):
    def __init__(self, *args, **kwargs):
        """Initialization that happens once per user.
        """
        super(TestBasic, self).__init__(*args, **kwargs)

        self.random_user = uuid.uuid4().hex
        self.basic_auth = HTTPBasicAuth(self.random_user, 'secret')

        # Create at least some records for this user
        total_records = random.randint(3, 100)
        for i in range(total_records):
            self.create()

    def setUp(self):
        # Pick a random record
        resp = self.session.get(self.api_url('articles'), auth=self.basic_auth)
        self.random_record = random.choice(resp.json()['items'])
        self.random_id = self.random_record['_id']
        self.random_url = self.api_url('articles/{0}'.format(self.random_id))

    def incr_counter(self, name):
        hit, user, current_hit, current_user = self.session.loads_status
        if current_user is None:
            return
        super(TestBasic, self).incr_counter(name)

    def api_url(self, path):
        return "{0}/v0/{1}".format(self.server_url, path)

    def test_all(self):
        # Pick a random action, with particular frequency
        action, percentage = random.choice(ACTIONS_FREQUENCIES)
        while random.randint(0, 100) > percentage:
            action, percentage = random.choice(ACTIONS_FREQUENCIES)

        getattr(self, action)()

    def create(self, prepare=False):
        suffix = uuid.uuid4().hex
        data = {
            "title": "Corp Site {0}".format(suffix),
            "url": "http://mozilla.org/{0}".format(suffix),
            "added_by": "FxOS-{0}".format(suffix),
        }
        resp = self.session.post(
            self.api_url('articles'),
            data,
            auth=self.basic_auth)
        self.assertEqual(resp.status_code, 201)
        self.incr_counter("created")

    def create_conflict(self):
        data = self.random_record.copy()
        data.pop('_id')
        resp = self.session.post(
            self.api_url('articles'),
            data,
            auth=self.basic_auth)
        self.assertEqual(resp.status_code, 201)  # XXX. 303
        self.incr_counter("create-conflict")

    def filter_sort(self):
        queries = [
            [('status', '0')],
            [('unread', 'true'), ('status', '0')],
            [('_sort', '-last_modified'), ('status', '1')],
            [('_sort', 'title')],
            [('_sort', '-added_by,-stored_on'), ('status', '0')],
        ]
        queryparams = random.choice(queries)
        query_url = '&'.join(['='.join(param) for param in queryparams])
        url = self.api_url('articles?{}'.format(query_url))
        resp = self.session.get(url, auth=self.basic_auth)
        self.assertEqual(resp.status_code, 200)

    def _patch(self, url, data, status=200):
        data = json.dumps(data)
        resp = self.session.patch(url, data, auth=self.basic_auth)
        self.assertEqual(resp.status_code, status)

    def update(self):
        data = {
            "title": "Some title {}".format(random.randint(0, 1)),
            "status": random.randint(0, 1),
            "is_article": bool(random.randint(0, 1)),
            "favorite": bool(random.randint(0, 1)),
        }
        self._patch(self.random_url, data)
        self.incr_counter("update-record")

    def read_further(self):
        data = {
            "read_position": random.randint(0, 10000)
        }
        self._patch(self.random_url, data)
        self.incr_counter("read-further")

    def mark_as_read(self):
        data = {
            "marked_read_by": "Desktop",
            "marked_read_on": 12345,
            "unread": False,
        }
        self._patch(self.random_url, data)
        self.incr_counter("marked-as-read")

    def update_conflict(self):
        data = {
            "resolved_url": "http://mozilla.org"  # XXX reuse existing
        }
        self._patch(self.random_url, data)
        self.incr_counter("update-conflict")

    def archive(self):
        data = {
            "status": 1
        }
        self._patch(self.random_url, data)

    def delete(self):
        resp = self.session.delete(self.random_url, auth=self.basic_auth)
        self.assertEqual(resp.status_code, 200)
        self.incr_counter("deleted")
