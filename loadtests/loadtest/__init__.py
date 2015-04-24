import json
import os
import random
import uuid

from requests.auth import HTTPBasicAuth, AuthBase
from loads.case import TestCase
from konfig import Config

ACTIONS_FREQUENCIES = [
    ('create', 20),
    ('batch_create', 50),
    ('update', 50),
    ('filter_sort', 60),
    ('read_further', 80),
    ('batch_read_further', 80),
    ('mark_as_read', 40),
    ('create_conflict', 10),
    ('update_conflict', 10),
    ('archive', 10),
    ('batch_archive', 30),
    ('delete', 10),
    ('batch_delete', 10),
    ('poll_changes', 90),
    ('list_archived', 20),
    ('list_deleted', 40),
    ('batch_count', 50),
    ('list_continuated_pagination', 80),
]


def build_article():
    suffix = uuid.uuid4().hex
    data = {
        "title": "Corp Site {0}".format(suffix),
        "url": "http://mozilla.org/{0}".format(suffix),
        "resolved_url": "http://mozilla.org/{0}".format(suffix),
        "added_by": "FxOS-{0}".format(suffix),
    }
    return data


class RawAuth(AuthBase):
    def __init__(self, authorization):
        self.authorization = authorization

    def __call__(self, r):
        r.headers['Authorization'] = self.authorization
        return r


class TestBasic(TestCase):
    def __init__(self, *args, **kwargs):
        """Initialization that happens once per user.

        :note:

            This method is called as many times as number of users.
        """
        super(TestBasic, self).__init__(*args, **kwargs)

        self.conf = self._get_configuration()

        if self.conf.get('smoke', False):
            self.random_user = "test@restmail.net"
            self.auth = RawAuth("Bearer %s" % self.conf.get('token'))
        else:
            self.random_user = uuid.uuid4().hex
            self.auth = HTTPBasicAuth(self.random_user, 'secret')

        # Create at least some records for this user
        self.nb_initial_records = random.randint(3, 100)

    def _get_configuration(self):
        # Loads is removing the extra information contained in the ini files,
        # so we need to parse it again.
        config_file = self.config['config']
        # When copying the configuration files, we lose the config/ prefix so,
        # try to read from this folder in case the file doesn't exist.
        if not os.path.isfile(config_file):
            config_file = os.path.basename(config_file)
            if not os.path.isfile(config_file):
                msg = 'Unable to locate the configuration file, aborting.'
                raise LookupError(msg)
        return Config(config_file).get_map('loads')

    def api_url(self, path):
        return "{0}/v1/{1}".format(self.server_url, path)

    def setUp(self):
        """Choose some random records in the whole collection.

        :note:

            This method is called as many times as number of hits.
        """
        nb_initial_records = self.nb_initial_records
        while nb_initial_records > 0:
            self.create()
            nb_initial_records -= 1

        resp = self.session.get(self.api_url('articles'), auth=self.auth)
        records = resp.json()['items']

        # Pick a random record
        self.random_record = random.choice(records)
        self.random_id = self.random_record['id']
        self.random_url = self.api_url('articles/%s' % self.random_id)

        # Pick another random, different
        records.remove(self.random_record)
        self.random_record_2 = random.choice(records)
        self.random_id_2 = self.random_record_2['id']
        self.random_url_2 = self.api_url('articles/%s' % self.random_id_2)

    def test_all(self):
        """Choose a random action among available, if not frequent enough,
        try again recursively.

        :note:

            This method is called as many times as number of hits.
        """
        action, percentage = random.choice(ACTIONS_FREQUENCIES)

        forced_action = os.getenv('LOAD_ACTION')
        if forced_action:
            action, percentage = forced_action, 101

        if random.randint(0, 100) < percentage:
            self.incr_counter(action)
            return getattr(self, action)()
        else:
            self.test_all()

    def _run_batch(self, data):
        resp = self.session.post(self.api_url('batch'),
                                 data=json.dumps(data),
                                 auth=self.auth,
                                 headers={'Content-Type': 'application/json'})
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)
        for subresponse in resp.json()['responses']:
            self.incr_counter(subresponse['status'])

    def create(self):
        data = build_article()
        resp = self.session.post(
            self.api_url('articles'),
            data,
            auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 201)

    def batch_create(self):
        data = {
            "defaults": {
                "method": "POST",
                "path": "/articles"
            }
        }
        for i in range(25):
            request = {"body": build_article()}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def create_conflict(self):
        data = self.random_record.copy()
        data.pop('id')
        resp = self.session.post(
            self.api_url('articles'),
            data,
            auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def filter_sort(self):
        queries = [
            [('archived', 'false')],
            [('unread', 'true'), ('archived', 'false')],
            [('_sort', '-last_modified'), ('archived', 'true')],
            [('_sort', 'title')],
            [('_sort', '-added_by,-stored_on'), ('archived', 'false')],
        ]
        queryparams = random.choice(queries)
        query_url = '&'.join(['='.join(param) for param in queryparams])
        url = self.api_url('articles?{}'.format(query_url))
        resp = self.session.get(url, auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def _patch(self, url, data, status=200):
        data = json.dumps(data)
        resp = self.session.patch(url, data, auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, status)

    def update(self):
        data = {
            "title": "Some title {}".format(random.randint(0, 1)),
            "archived": bool(random.randint(0, 1)),
            "is_article": bool(random.randint(0, 1)),
            "favorite": bool(random.randint(0, 1)),
        }
        self._patch(self.random_url, data)

    def read_further(self):
        data = {
            "read_position": random.randint(0, 10000)
        }
        self._patch(self.random_url, data)

    def batch_read_further(self):
        # Get some random articles on which the batch will be applied
        url = self.api_url('articles?_limit=5&_sort=title')
        resp = self.session.get(url, auth=self.auth)
        articles = resp.json()['items']
        urls = ['/articles/{}'.format(a['id']) for a in articles]

        data = {
            "defaults": {
                "method": "PATCH",
            }
        }
        for i in range(25):
            request = {
                "path": urls[i % len(urls)],
                "body": {
                    "read_position": random.randint(0, 10000)
                }
            }
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def mark_as_read(self):
        data = {
            "marked_read_by": "Desktop",
            "marked_read_on": 12345,
            "unread": False,
        }
        self._patch(self.random_url, data)

    def update_conflict(self):
        random_resolved_url = self.random_record_2['resolved_url']
        data = {
            "resolved_url": random_resolved_url
        }
        self._patch(self.random_url, data, status=409)

    def archive(self):
        data = {
            "archived": "true"
        }
        self._patch(self.random_url, data)

    def batch_archive(self):
        data = {
            "defaults": {
                "method": "PATCH",
                "body": {"archived": "true"}
            },
            "requests": [
                {"path": '/articles/%s' % self.random_id},
                {"path": '/articles/%s' % self.random_id_2}
            ]
        }
        self._run_batch(data)

    def delete(self):
        resp = self.session.delete(self.random_url, auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def batch_delete(self):
        # Get some random articles on which the batch will be applied
        url = self.api_url('articles?_limit=5&_sort=title')
        resp = self.session.get(url, auth=self.auth)
        articles = resp.json()['items']
        urls = ['/articles/{}'.format(a['id']) for a in articles]

        data = {
            "defaults": {
                "method": "DELETE"
            }
        }
        for i in range(25):
            request = {"path": urls[i % len(urls)]}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def poll_changes(self):
        last_modified = self.random_record['last_modified']
        modified_url = self.api_url('articles?_since=%s' % last_modified)
        resp = self.session.get(modified_url, auth=self.auth)
        self.assertEqual(resp.status_code, 200)

    def list_archived(self):
        archived_url = self.api_url('articles?archived=true')
        resp = self.session.get(archived_url, auth=self.auth)
        self.assertEqual(resp.status_code, 200)

    def batch_count(self):
        data = {
            "defaults": {
                "method": "HEAD",
            },
            "requests": [
                {"path": "/articles?archived=true"},
                {"path": "/articles?is_article=true"},
                {"path": "/articles?favorite=true"},
                {"path": "/articles?unread=false"},
                {"path": "/articles?min_read_position=100"}
            ]
        }
        self._run_batch(data)

    def list_deleted(self):
        modif = self.random_record['last_modified']
        deleted_url = self.api_url('articles?_since=%s&deleted=true' % modif)
        resp = self.session.get(deleted_url, auth=self.auth)
        self.assertEqual(resp.status_code, 200)

    def list_continuated_pagination(self):
        paginated_url = self.api_url('articles?_limit=20')

        while paginated_url:
            resp = self.session.get(paginated_url, auth=self.auth)
            self.assertEqual(resp.status_code, 200)
            next_page = resp.headers.get("Next-Page")
            self.assertNotEqual(paginated_url, next_page)
            paginated_url = next_page
