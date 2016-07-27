import json
import os
import random
import uuid

from . import BaseLoadTest

ACTIONS_FREQUENCIES = [
    ('create', 20),
    ('create_put', 20),
    ('batch_create', 50),
    ('batch_create_put', 50),
    ('batch_replace', 50),
    ('batch_update', 50),
    ('update', 50),
    ('filter_sort', 60),
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


class SimulationLoadTest(BaseLoadTest):

    def __init__(self, *args, **kwargs):
        super(SimulationLoadTest, self).__init__(*args, **kwargs)
        self.collection = 'articles'
        self.init_user()

    def init_user(self, *args, **kwargs):
        """Initialization that happens once per user.

        :note:

            This method is called as many times as number of users.
        """
        # Create at least some records for this user
        max_initial_records = self.conf.get('max_initial_records', 100)
        self.nb_initial_records = random.randint(3, max_initial_records)
        self.batch_requests_size = self.conf.get('batch_requests_size', 25)

        self.bucket = os.getenv('BUCKET', self.conf.get('bucket', 'default'))
        if self.bucket != 'default':
            # Create bucket + collection:
            self.collection_url()

    def _pickRecords(self):
        resp = self.session.get(self.collection_url())
        self.records = resp.json()['data']

        # Create some records, if not any in collection.
        if len(self.records) < self.nb_initial_records:
            for i in range(self.nb_initial_records):
                self.create()
            resp = self.session.get(self.collection_url())
            self.records = resp.json()['data']

        # Pick a random record
        self.random_record = random.choice(self.records)
        self.random_id = self.random_record['id']
        self.random_url = self.record_url(self.random_id)

        # Pick another random, different
        self.records.remove(self.random_record)
        self.random_record_2 = random.choice(self.records)
        self.random_id_2 = self.random_record_2['id']
        self.random_url_2 = self.record_url(self.random_id_2)

    def setUp(self):
        """Choose some random records in the whole collection.

        :note:

            This method is called as many times as number of hits.
        """
        pass

    def test_simulation(self):
        """
        :note:

            This method is called as many times as number of hits.
        """
        preset = os.getenv('LOAD_PRESET', self.conf.get('preset', 'random'))

        rand = random.randint(0, 100)
        if preset == 'random':
            # Choose a random action among available, if not frequent enough,
            # try again recursively.
            action, percentage = random.choice(ACTIONS_FREQUENCIES)
            if rand < percentage:
                self.incr_counter(action)
                return getattr(self, action)()
            else:
                self.test_simulation()

        elif preset == "exhaustive":
            # Make sure we exhaustive every action.
            actions = [a for (a, _) in ACTIONS_FREQUENCIES]
            for action in actions:
                getattr(self, action)()

        elif preset == "read":
            if rand < 2:
                action = 'batch_create_put'
            elif rand < 80:
                action = 'poll_changes'
            elif rand < 90:
                action = 'list_deleted'
            else:
                action = 'filter_sort'
            self.incr_counter(action)
            getattr(self, action)()

        elif preset == "write":
            if rand < 20:
                action = 'batch_create'
            elif rand < 40:
                action = 'batch_create_put'
            elif rand < 60:
                action = 'batch_replace'
            elif rand < 90:
                action = 'batch_delete'
            else:
                action = 'poll_changes'
            self.incr_counter(action)
            getattr(self, action)()

    def create(self):
        article = build_article()
        resp = self.session.post(
            self.collection_url(),
            data=json.dumps({'data': article}),
            headers={'Content-Type': 'application/json'})
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 201)

    def create_put(self):
        article = build_article()
        resp = self.session.put(
            self.record_url(uuid.uuid4()),
            data=json.dumps({'data': article}),
            headers={'Content-Type': 'application/json'})
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 201)

    def batch_create(self):
        data = {
            "defaults": {
                "method": "POST",
                "path": self.collection_url(prefix=False)
            }
        }
        for i in range(self.batch_requests_size):
            request = {"body": {"data": build_article()}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def batch_create_put(self):
        data = {
            "defaults": {
                "method": "PUT",
            }
        }
        for i in range(self.batch_requests_size):
            path = self.record_url(uuid.uuid4(), prefix=False)
            request = {"path": path, "body": {"data": build_article()}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

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
        url = self.collection_url() + '?' + query_url
        resp = self.session.get(url)
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def _patch(self, url, data, status=200):
        data = json.dumps(data)
        resp = self.session.patch(url, data)
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, status)

    def _run_batch(self, data):
        resp = self.session.post(self.api_url('batch'),
                                 data=json.dumps(data))
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        for subresponse in resp.json()['responses']:
            self.incr_counter('status-%s' % subresponse['status'])

    def update(self):
        self._pickRecords()
        data = {
            "title": "Some title {}".format(random.randint(0, 1)),
            "archived": bool(random.randint(0, 1)),
            "is_article": bool(random.randint(0, 1)),
            "favorite": bool(random.randint(0, 1)),
        }
        self._patch(self.random_url, {"data": data})

    def batch_replace(self):
        self._pickRecords()
        data = {
            "defaults": {
                "method": "PUT"
            }
        }
        nb_batched = min(self.nb_initial_records, len(self.records))
        records = random.sample(self.records, nb_batched)
        for record in records:
            record_url = self.record_url(record['id'], prefix=False)
            request = {"path": record_url, "body": {"data": build_article()}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def batch_update(self):
        self._pickRecords()
        data = {
            "defaults": {
                "method": "PATCH"
            }
        }
        nb_batched = min(self.nb_initial_records, len(self.records))
        records = random.sample(self.records, nb_batched)
        for record in records:
            record_url = self.record_url(record['id'], prefix=False)
            change = {"title": "Some title %s" % random.randint(0, 100)}
            request = {"path": record_url, "body": {"data": change}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def delete(self):
        self._pickRecords()
        resp = self.session.delete(self.random_url)
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def batch_delete(self):
        self._pickRecords()
        # Get some random articles on which the batch will be applied
        nb_deleted = min(self.nb_initial_records, len(self.records))
        records = random.sample(self.records, nb_deleted)
        data = {
            "defaults": {
                "method": "DELETE"
            }
        }
        for record in records[:self.batch_requests_size]:
            request = {"path": self.record_url(record['id'], prefix=False)}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def poll_changes(self):
        self._pickRecords()
        last_modified = self.random_record['last_modified']
        filters = '?_since=%s' % last_modified
        modified_url = self.collection_url() + filters
        resp = self.session.get(modified_url)
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def list_archived(self):
        archived_url = self.collection_url() + '?archived=true'
        resp = self.session.get(archived_url)
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def batch_count(self):
        base_url = self.collection_url(prefix=False)
        data = {
            "defaults": {
                "method": "HEAD",
            },
            "requests": [
                {"path": base_url + "?archived=true"},
                {"path": base_url + "?is_article=true"},
                {"path": base_url + "?favorite=true"},
                {"path": base_url + "?unread=false"},
                {"path": base_url + "?min_read_position=100"}
            ]
        }
        self._run_batch(data)

    def list_deleted(self):
        self._pickRecords()
        modif = self.random_record['last_modified']
        filters = '?_since=%s&deleted=true' % modif
        deleted_url = self.collection_url() + filters
        resp = self.session.get(deleted_url)
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def list_continuated_pagination(self):
        paginated_url = self.collection_url() + '?_limit=20'
        while paginated_url:
            resp = self.session.get(paginated_url)
            self.incr_counter('status-%s' % resp.status_code)
            self.assertEqual(resp.status_code, 200)
            next_page = resp.headers.get("Next-Page")
            self.assertNotEqual(paginated_url, next_page)
            paginated_url = next_page
