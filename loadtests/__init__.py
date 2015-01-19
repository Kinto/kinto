import json
import random
import uuid

from requests.auth import HTTPBasicAuth
from loads.case import TestCase


PERCENTAGE_OF_CREATION = 20
PERCENTAGE_OF_UPDATE = 50
PERCENTAGE_OF_FILTERING = 60
PERCENTAGE_OF_READ_POSITION = 80
PERCENTAGE_OF_MARKING_AS_READ = 40
PERCENTAGE_OF_ARCHIVING = 10
PERCENTAGE_OF_DELETING = 10
PERCENTAGE_OF_CONFLICT_CREATION = 10
PERCENTAGE_OF_CONFLICT_UPDATE = 10


class TestBasic(TestCase):
    available_users = [
        ('alice', 'secret'),
        ('bob', 'secret'),
        ('charlie', 'secret')
    ]

    def __init__(self, *args, **kwargs):
        super(TestBasic, self).__init__(*args, **kwargs)

        self.random_user = None

        # Create at least one record per user
        for user in self.available_users:
            self.basic_auth = HTTPBasicAuth(*user)
            self.test_create_record()

    def setUp(self):
        # Change current user randomly
        self.random_user = random.choice(self.available_users)
        self.basic_auth = HTTPBasicAuth(*self.random_user)

        resp = self.session.get(self.api_url('articles'), auth=self.basic_auth)
        self.random_record = random.choice(resp.json()['items'])
        self.random_id = self.random_record['_id']
        self.random_url = self.api_url('articles/{0}'.format(self.random_id))

    def incr_counter(self, name):
        if not self.random_user:
            return
        name = "{} {}".format(self.random_user[0], name)
        super(TestBasic, self).incr_counter(name)

    def api_url(self, path):
        return "{0}/v0/{1}".format(self.server_url, path)

    def test_all(self):
        if random.randint(0, 100) < PERCENTAGE_OF_CREATION:
            self.test_create_record()

        if random.randint(0, 100) < PERCENTAGE_OF_UPDATE:
            self.test_update_record()

        if random.randint(0, 100) < PERCENTAGE_OF_CONFLICT_CREATION:
            self.test_create_conflicting_record()

        if random.randint(0, 100) < PERCENTAGE_OF_FILTERING:
            self.test_filter_and_sort_list()

        if random.randint(0, 100) < PERCENTAGE_OF_READ_POSITION:
            self.test_update_read_position()

        if random.randint(0, 100) < PERCENTAGE_OF_MARKING_AS_READ:
            self.test_mark_as_read()

        if random.randint(0, 100) < PERCENTAGE_OF_CONFLICT_UPDATE:
            self.test_conflicting_update()

        if random.randint(0, 100) < PERCENTAGE_OF_ARCHIVING:
            self.test_archive()

        if random.randint(0, 100) < PERCENTAGE_OF_DELETING:
            self.test_delete()

    def test_create_record(self, prepare=False):
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

    def test_create_conflicting_record(self):
        data = self.random_record.copy()
        data.pop('_id')
        resp = self.session.post(
            self.api_url('articles'),
            data,
            auth=self.basic_auth)
        self.assertEqual(resp.status_code, 201)  # XXX. 303
        self.incr_counter("create-conflict")

    def test_filter_and_sort_list(self):
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

    def test_update_record(self):
        data = {
            "title": "Some title {}".format(random.randint(0, 1)),
            "status": random.randint(0, 1),
            "is_article": bool(random.randint(0, 1)),
            "favorite": bool(random.randint(0, 1)),
        }
        self._patch(self.random_url, data)
        self.incr_counter("update-record")

    def test_update_read_position(self):
        data = {
            "read_position": random.randint(0, 10000)
        }
        self._patch(self.random_url, data)
        self.incr_counter("read-further")

    def test_mark_as_read(self):
        data = {
            "marked_read_by": "Desktop",
            "marked_read_on": 12345,
            "unread": False,
        }
        self._patch(self.random_url, data)
        self.incr_counter("marked-as-read")

    def test_conflicting_update(self):
        data = {
            "resolved_url": "http://mozilla.org"  # XXX reuse existing
        }
        self._patch(self.random_url, data)
        self.incr_counter("update-conflict")

    def test_archive(self):
        data = {
            "status": 1
        }
        self._patch(self.random_url, data)

    def test_delete(self):
        resp = self.session.delete(self.random_url, auth=self.basic_auth)
        self.assertEqual(resp.status_code, 200)
        self.incr_counter("deleted")
