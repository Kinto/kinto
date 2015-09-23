import json
import os
import random
import uuid

from . import BaseLoadTest

ACTIONS_FREQUENCIES = [
    ('create', 20),
    ('batch_create', 50),
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
        self.init_article()

    def init_article(self, *args, **kwargs):
        """Initialization that happens once per user.

        :note:

            This method is called as many times as number of users.
        """
        # Create at least some records for this user
        max_initial_records = self.conf.get('max_initial_records', 100)
        self.nb_initial_records = random.randint(3, max_initial_records)

    def setUp(self):
        """Choose some random records in the whole collection.

        :note:

            This method is called as many times as number of hits.
        """
        resp = self.session.get(self.collection_url())
        records = resp.json()['data']

        # Create some records, if not any in collection.
        if len(records) < self.nb_initial_records:
            for i in range(self.nb_initial_records):
                self.create()
            resp = self.session.get(self.collection_url())
            records = resp.json()['data']

        # Pick a random record
        self.random_record = random.choice(records)
        self.random_id = self.random_record['id']
        self.random_url = self.record_url(self.random_id)

        # Pick another random, different
        records.remove(self.random_record)
        self.random_record_2 = random.choice(records)
        self.random_id_2 = self.random_record_2['id']
        self.random_url_2 = self.record_url(self.random_id_2)

    def test_simulation(self):
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
            self.test_simulation()

    def create(self):
        article = build_article()
        resp = self.session.post(
            self.collection_url(),
            data=json.dumps({'data': article}),
            headers={'Content-Type': 'application/json'})
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 201)

    def batch_create(self):
        data = {
            "defaults": {
                "method": "POST",
                "path": self.collection_url(prefix=False)
            }
        }
        for i in range(25):
            request = {"body": {"data": build_article()}}
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
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def _patch(self, url, data, status=200):
        data = json.dumps(data)
        resp = self.session.patch(url, data)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, status)

    def _run_batch(self, data):
        resp = self.session.post(self.api_url('batch'),
                                 data=json.dumps(data))
        self.incr_counter('status-%s' % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        for subresponse in resp.json()['responses']:
            self.incr_counter('status-%s' % subresponse['status'])

    def update(self):
        data = {
            "title": "Some title {}".format(random.randint(0, 1)),
            "archived": bool(random.randint(0, 1)),
            "is_article": bool(random.randint(0, 1)),
            "favorite": bool(random.randint(0, 1)),
        }
        self._patch(self.random_url, {"data": data})

    def delete(self):
        resp = self.session.delete(self.random_url)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def batch_delete(self):
        # Get some random articles on which the batch will be applied
        url = self.collection_url() + '?_limit=5&_sort=title'
        resp = self.session.get(url)
        articles = resp.json()['data']
        urls = [self.record_url(a['id'], prefix=False)
                for a in articles]

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
        filters = '?_since=%s' % last_modified
        modified_url = self.collection_url() + filters
        resp = self.session.get(modified_url)
        self.assertEqual(resp.status_code, 200)

    def list_archived(self):
        archived_url = self.collection_url() + '?archived=true'
        resp = self.session.get(archived_url)
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
        modif = self.random_record['last_modified']
        filters = '?_since=%s&deleted=true' % modif
        deleted_url = self.collection_url() + filters
        resp = self.session.get(deleted_url)
        self.assertEqual(resp.status_code, 200)

    def list_continuated_pagination(self):
        paginated_url = self.collection_url() + '?_limit=20'

        urls = []

        while paginated_url:
            resp = self.session.get(paginated_url)
            self.assertEqual(resp.status_code, 200)
            next_page = resp.headers.get("Next-Page")
            if next_page is not None and next_page not in urls:
                self.assertNotEqual(paginated_url, next_page)
                paginated_url = next_page
                urls.append(next_page)
            else:
                # XXX: we shouldn't have to keep the full list.
                # See mozilla-services/cliquet#366
                break
