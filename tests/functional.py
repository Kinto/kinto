import os.path
from urllib.parse import urljoin

import random
import re
import unittest
import uuid

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

    def test_user_shared_bucket_tutorial(self):
        bucket_id = 'bucket-%s' % uuid.uuid4()
        collection_id = 'tasks-%s' % uuid.uuid4()
        bucket_url = urljoin(self.server_url, '/buckets/{}'.format(bucket_id))
        collection_url = '{}/collections/{}/records'.format(bucket_url, collection_id)

        # Create a new bucket and check for permissions
        resp = self.session.put(bucket_url)
        # In case of concurrent execution, it may have been created already.
        self.assertIn(resp.status_code, (200, 201))
        bucket = resp.json()
        self.assertIn('write', bucket['permissions'])

        # Create a new collection and check for permissions
        permissions = {"record:create": ['system.Authenticated']}
        resp = self.session.put(
            re.sub('/records$', '', collection_url),
            json={'permissions': permissions})
        # In case of concurrent execution, it may have been created already.
        self.assertIn(resp.status_code, (200, 201))
        collection = resp.json()
        self.assertIn('record:create', collection['permissions'])
        self.assertIn('system.Authenticated',
                      collection['permissions']['record:create'])

        # Create a new tasks for Alice
        alice_auth = ('token', 'alice-secret-%s' % uuid.uuid4())
        alice_task = build_task()
        resp = self.session.post(
            collection_url,
            json={'data': alice_task},
            auth=alice_auth)
        self.assertEqual(resp.status_code, 201)
        collection = resp.json()
        self.assertIn('write', collection['permissions'])
        alice_task_id = collection['data']['id']

        bob_auth = ('token', 'bob-secret-%s' % uuid.uuid4())

        # Bob has no task yet.
        resp = self.session.get(collection_url, auth=bob_auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['data']), 0)

        # Create a new tasks for Bob
        bob_task = build_task()
        resp = self.session.post(
            collection_url,
            json={'data': bob_task},
            auth=bob_auth)
        self.assertEqual(resp.status_code, 201)
        collection = resp.json()
        self.assertIn('write', collection['permissions'])
        bob_user_id = collection['permissions']['write'][0]
        bob_task_id = collection['data']['id']

        # Now that he has a task, he should see his.
        resp = self.session.get(collection_url, auth=bob_auth)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], bob_task_id)

        record_url = '{}/{}'.format(collection_url, alice_task_id)

        # Share Alice's task with Bob
        resp = self.session.patch(record_url,
                                  json={'permissions': {'read': [bob_user_id]}},
                                  auth=alice_auth)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertIn('write', record['permissions'])
        alice_task_id = record['data']['id']

        # Check that Bob can access it
        resp = self.session.get(record_url, auth=bob_auth)
        self.assertEqual(resp.status_code, 200)

        # Get mary's userid
        mary_auth = ('token', 'mary-secret-%s' % uuid.uuid4())
        resp = self.session.get('{}/'.format(self.server_url), auth=mary_auth)
        self.assertEqual(resp.status_code, 200)
        hello = resp.json()
        mary_user_id = hello['user']['id']

        # Allow group creation on bucket
        permissions = {"group:create": ['system.Authenticated']}
        resp = self.session.put(bucket_url,
                                json={'permissions': permissions})
        self.assertEqual(resp.status_code, 200)
        bucket = resp.json()
        self.assertIn('group:create', bucket['permissions'])
        self.assertIn('system.Authenticated',
                      bucket['permissions']['group:create'])

        # Create Alice's friend group with Bob and Mary
        group_url = '{}/groups/alices-friends'.format(bucket_url)
        resp = self.session.put(group_url,
                                json={'data': {'members': [mary_user_id, bob_user_id]}},
                                auth=alice_auth)
        self.assertEqual(resp.status_code, 201)

        # Give Alice's task permission for that group
        group_id = '/buckets/{}/groups/alices-friends'.format(bucket_id)
        resp = self.session.patch(record_url,
                                  json={'permissions': {'read': [group_id]}},
                                  auth=alice_auth)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertIn(group_id, record['permissions']['read'])

        # Try to access Alice's task with Mary
        resp = self.session.get(record_url, auth=mary_auth)
        self.assertEqual(resp.status_code, 200)

        # Check that Mary's collection_get sees Alice's task
        resp = self.session.get(collection_url, auth=mary_auth)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], alice_task_id)

        # Check that Bob's collection_get sees both his and Alice's tasks
        resp = self.session.get(collection_url, auth=bob_auth)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 2)
        records_ids = [r['id'] for r in records]
        self.assertIn(alice_task_id, records_ids)
        self.assertIn(bob_task_id, records_ids)

    def test_check_for_lists(self):
        # List buckets should not be forbidden
        resp = self.session.get('{}/buckets'.format(self.server_url))
        self.assertEqual(resp.status_code, 200)
