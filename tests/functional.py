import os.path
from six.moves.urllib.parse import urljoin

import uuid
import random
import unittest
import requests


__HERE__ = os.path.abspath(os.path.dirname(__file__))

SERVER_URL = "http://localhost:8888/v1"
DEFAULT_AUTH = ('user', 'p4ssw0rd')


def build_task():
    suffix = str(uuid.uuid4())
    data = {
        "description": "Task description {0}".format(suffix),
        "status": random.choice(("todo", "doing")),
    }
    return data


class FunctionalTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(FunctionalTest, self).__init__(*args, **kwargs)
        # XXX Read the configuration from env variables.
        self.server_url = SERVER_URL
        self.auth = DEFAULT_AUTH
        self.session = requests.Session()
        self.session.auth = DEFAULT_AUTH

    def tearDown(self):
        # Delete all the created objects
        flush_url = urljoin(self.server_url, '/__flush__')
        resp = requests.post(flush_url)
        resp.raise_for_status()

    def test_user_default_bucket_tutorial(self):
        collection_id = 'tasks-%s' % uuid.uuid4()
        collection_url = urljoin(self.server_url,
                                 '/buckets/default/collections/{}/records'.format(collection_id))
        task = build_task()

        # Create a task on a default collection
        # 201 created with data and permission.write
        resp = self.session.post(collection_url, json={"data": task})
        resp.raise_for_status()
        self.assertEquals(resp.status_code, 201)
        record = resp.json()

        self.assertEquals(record['data']['description'], task['description'])
        self.assertEquals(record['data']['status'], task['status'])
        self.assertIn('write', record['permissions'])

        # Create a new one with PUT and If-None-Match: "*"
        task = build_task()
        record_id = str(uuid.uuid4())
        record_url = urljoin(self.server_url,
                             '{}/{}'.format(collection_url, record_id))
        resp = self.session.put(record_url, json={'data': task},
                                headers={'If-None-Match': '*'})
        resp.raise_for_status()
        resp.raise_for_status()
        self.assertEquals(resp.status_code, 201)
        record = resp.json()

        self.assertEquals(record['data']['description'], task['description'])
        self.assertEquals(record['data']['status'], task['status'])
        self.assertIn('write', record['permissions'])

        # Fetch the collection list and see the tasks (save the etag)
        resp = self.session.get(collection_url)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(len(record['data']), 2)
        etag = resp.headers['ETag']

        # Fetch the collection from the Etag and see nothing new
        resp = self.session.get(
            collection_url,
            params={'_since': etag.strip('"')})
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(len(record['data']), 0)

        # Update a task
        resp = self.session.patch(
            record_url,
            json={'data': {'status': 'done'}})
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(record['data']['status'], 'done')
        self.assertIn('write', record['permissions'])

        # Try an update with If-Match on the saved ETag and see it fails
        resp = self.session.patch(
            record_url,
            json={'data': {'status': 'done'}},
            headers={'If-Match': etag})
        self.assertEqual(resp.status_code, 412)
        self.assertEqual(resp.headers['ETag'],
                         '"%s"' % record['data']['last_modified'])

        # Get the list of records and update the ETag
        resp = self.session.get(
            '%s?_since=%s' % (collection_url, etag.strip('"')))
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(len(record['data']), 1)
        etag = resp.headers['ETag']

        # Try an update with If-Match on the new ETag and see it works
        resp = self.session.patch(
            record_url,
            json={'data': {'status': 'done'}},
            headers={'If-Match': etag})
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        etag = resp.headers['ETag']

        # Delete the record with If-Match
        resp = self.session.delete(
            record_url,
            headers={'If-Match': etag})

        self.assertEqual(resp.status_code, 200)

        # Try the collection get with the ``_since`` parameter
        resp = self.session.get(
            '%s?_since=%s' % (collection_url, etag.strip('"')),
            headers={'If-None-Match': etag})
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(len(record['data']), 1)
        self.assertIn('deleted', record['data'][0])

        # Delete all the things
        resp = self.session.delete(collection_url)
        self.assertEqual(resp.status_code, 200)
