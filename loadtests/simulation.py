import json
import os
import random
import uuid

from konfig import Config
from loads.case import TestCase
from requests.auth import HTTPBasicAuth


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
    ('list_deleted', 40),
    ('batch_count', 50),
    ('list_continuated_pagination', 80),
]


def build_record():
    suffix = uuid.uuid4().hex
    data = {
        "name": "Mushroom {0}".format(suffix),
        "editable": (random.randint(0, 1) == 0),
        "size": random.randint(0, 10),
    }
    return data


class SimulationLoadTest(TestCase):

    def __init__(self, *args, **kwargs):
        super(SimulationLoadTest, self).__init__(*args, **kwargs)

        self.conf = self._get_configuration()

        self.random_user = uuid.uuid4().hex
        self.auth = HTTPBasicAuth(self.random_user, 'secret')
        self.session.auth = self.auth
        self.session.headers.update({'Content-Type': 'application/json'})

        self.collection = 'psilos'
        self.init_record()

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
        url = "{0}/v0/{1}".format(self.server_url.rstrip('/'), path)
        return url

    def collection_url(self, prefix=True):
        if prefix:
            return self.api_url(self.collection)
        return '/' + self.collection

    def record_url(self, record_id, prefix=True):
        return self.collection_url(prefix) + '/%s' % record_id

    def init_record(self, *args, **kwargs):
        """Initialization that happens once per user.

        :note:

            This method is called as many times as number of users.
        """
        # Create at least some records for this user
        max_initial_records = self.conf.get('max_initial_records', 100)
        self.nb_initial_records = random.randint(3, max_initial_records)
        self.batch_requests_size = self.conf.get('batch_requests_size', 25)

    def setUp(self):
        """Choose some random records in the whole collection.

        :note:

            This method is called as many times as number of hits.
        """
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
        record = build_record()
        resp = self.session.post(
            self.collection_url(),
            data=json.dumps({'data': record}),
            headers={'Content-Type': 'application/json'})
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 201)

    def create_put(self):
        record = build_record()
        resp = self.session.put(
            self.record_url(uuid.uuid4()),
            data=json.dumps({'data': record}),
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
        for i in range(self.batch_requests_size):
            request = {"body": {"data": build_record()}}
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
            request = {"path": path, "body": {"data": build_record()}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def filter_sort(self):
        queries = [
            [('edible', 'false')],
            [('edible', 'true'), ('min_size', '3')],
            [('_sort', '-last_modified'), ('max_size', '5')],
            [('_sort', 'name')],
            [('_sort', '-size,-name'), ('edible', 'false')],
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
            "name": "Some title {}".format(random.randint(0, 1)),
            "edible": bool(random.randint(0, 1)),
            "size": random.randint(10, 20),
        }
        self._patch(self.random_url, {"data": data})

    def batch_replace(self):
        data = {
            "defaults": {
                "method": "PUT"
            }
        }
        nb_batched = min(self.nb_initial_records, len(self.records))
        records = random.sample(self.records, nb_batched)
        for record in records:
            record_url = self.record_url(record['id'], prefix=False)
            request = {"path": record_url, "body": {"data": build_record()}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def batch_update(self):
        data = {
            "defaults": {
                "method": "PATCH"
            }
        }
        nb_batched = min(self.nb_initial_records, len(self.records))
        records = random.sample(self.records, nb_batched)
        for record in records:
            record_url = self.record_url(record['id'], prefix=False)
            change = {"name": "Name %s" % random.randint(0, 100)}
            request = {"path": record_url, "body": {"data": change}}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def delete(self):
        resp = self.session.delete(self.random_url)
        self.incr_counter(resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def batch_delete(self):
        # Get some random records on which the batch will be applied
        url = self.collection_url() + '?_limit=5&_sort=name'
        resp = self.session.get(url)
        records = resp.json()['data']
        urls = [self.record_url(a['id'], prefix=False)
                for a in records]

        data = {
            "defaults": {
                "method": "DELETE"
            }
        }
        for i in range(self.batch_requests_size):
            request = {"path": urls[i % len(urls)]}
            data.setdefault("requests", []).append(request)

        self._run_batch(data)

    def poll_changes(self):
        last_modified = self.random_record['last_modified']
        filters = '?_since=%s' % last_modified
        modified_url = self.collection_url() + filters
        resp = self.session.get(modified_url)
        self.assertEqual(resp.status_code, 200)

    def batch_count(self):
        base_url = self.collection_url(prefix=False)
        data = {
            "defaults": {
                "method": "HEAD",
            },
            "requests": [
                {"path": base_url + "?edible=true"},
                {"path": base_url + "?min_size=5"}
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
