import json
import os
import random
import uuid

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


class ArticleLoadTestMixin(object):

    def init_article(self, *args, **kwargs):
        """Initialization that happens once per user.

        :note:

            This method is called as many times as number of users.
        """
        # Create at least some records for this user
        max_initial_records = self.conf.get('max_initial_records', 100)
        self.nb_initial_records = random.randint(3, max_initial_records)

        self.bucket = 'default'
        self.collection = 'articles'

        # Keep track of created objects.
        self._collections_created = {}

    def setUp(self):
        """Choose some random records in the whole collection.

        :note:

            This method is called as many times as number of hits.
        """
        resp = self.session.get(self.collection_url(), auth=self.auth)
        records = resp.json()['data']

        # Create some records, if not any in collection.
        if len(records) < self.nb_initial_records:
            for i in range(self.nb_initial_records):
                self.create()
            resp = self.session.get(self.collection_url(), auth=self.auth)
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

    def play_a_random_endpoint(self):
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
            self.play_a_random_endpoint()

    def create(self):
        article = build_article()
        resp = self.session.post(
            self.collection_url(),
            data=json.dumps({'data': article}),
            auth=self.auth,
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
        resp = self.session.get(url, auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def update(self):
        data = {
            "title": "Some title {}".format(random.randint(0, 1)),
            "archived": bool(random.randint(0, 1)),
            "is_article": bool(random.randint(0, 1)),
            "favorite": bool(random.randint(0, 1)),
        }
        self._patch(self.random_url, data)

    def delete(self):
        resp = self.session.delete(self.random_url, auth=self.auth)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def batch_delete(self):
        # Get some random articles on which the batch will be applied
        url = self.collection_url() + '?_limit=5&_sort=title'
        resp = self.session.get(url, auth=self.auth)
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
        resp = self.session.get(modified_url, auth=self.auth)
        self.assertEqual(resp.status_code, 200)

    def list_archived(self):
        archived_url = self.collection_url() + '?archived=true'
        resp = self.session.get(archived_url, auth=self.auth)
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
        resp = self.session.get(deleted_url, auth=self.auth)
        self.assertEqual(resp.status_code, 200)

    def list_continuated_pagination(self):
        paginated_url = self.collection_url() + '?_limit=20'

        while paginated_url:
            resp = self.session.get(paginated_url, auth=self.auth)
            self.assertEqual(resp.status_code, 200)
            next_page = resp.headers.get("Next-Page")
            self.assertNotEqual(paginated_url, next_page)
            paginated_url = next_page
