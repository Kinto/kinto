import json
import random
import re
import uuid

from requests.auth import HTTPBasicAuth
from . import BaseLoadTest


def build_task():
    suffix = unicode(uuid.uuid4())
    data = {
        "description": "Task description {0}".format(suffix),
        "status": random.choice(("todo", "doing")),
    }
    return data


class TutorialLoadTest(BaseLoadTest):
    def test_tutorial(self):
        self.play_user_default_bucket_tutorial()
        self.play_user_shared_bucket_tutorial()
        self.check_for_lists()

    def play_user_default_bucket_tutorial(self):
        collection_id = 'tasks-%s' % uuid.uuid4()
        collection_url = self.collection_url('default', collection_id)

        # Create a new task
        # 201 created with data and permission.write
        task = build_task()
        resp = self.session.post(
            collection_url,
            data=json.dumps({'data': task}))
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
        record = resp.json()
        self.assertEqual(record['data']['description'], task['description'])
        self.assertEqual(record['data']['status'], task['status'])
        self.assertIn('write', record['permissions'])

        # Create a new one with PUT and If-None-Match: "*"
        task = build_task()
        record_id = unicode(uuid.uuid4())
        record_url = self.record_url(record_id, 'default', collection_id)
        resp = self.session.put(
            record_url,
            data=json.dumps({'data': task}),
            headers={'If-None-Match': '*'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
        record = resp.json()
        self.assertEqual(record['data']['description'], task['description'])
        self.assertEqual(record['data']['status'], task['status'])
        self.assertIn('write', record['permissions'])

        # Fetch the collection list and see the tasks (save the etag)
        resp = self.session.get(collection_url)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 2)
        etag = resp.headers['ETag']

        # Fetch the collection from the Etag and see nothing new
        resp = self.session.get(
            collection_url,
            params={'_since': etag.strip('"')})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 0)

        # Update a task
        resp = self.session.patch(
            record_url,
            data=json.dumps({'data': {'status': 'done'}}))
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(record['data']['status'], 'done')
        self.assertIn('write', record['permissions'])

        # Try an update with If-Match on the saved ETag and see it fails
        resp = self.session.patch(
            record_url,
            data=json.dumps({'data': {'status': 'done'}}),
            headers={'If-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 412)
        self.assertEqual(resp.headers['ETag'],
                         '"%s"' % record['data']['last_modified'])

        # Get the list of records and update the ETag
        resp = self.session.get(
            '%s?_since=%s' % (collection_url, etag.strip('"')))
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        etag = resp.headers['ETag']

        # Try an update with If-Match on the new ETag and see it works
        resp = self.session.patch(
            record_url,
            data=json.dumps({'data': {'status': 'done'}}),
            headers={'If-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()['data']
        etag = resp.headers['ETag']

        # Delete the record with If-Match
        resp = self.session.delete(
            record_url,
            headers={'If-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)

        # Try the collection get with the ``_since`` parameter
        resp = self.session.get(
            '%s?_since=%s' % (collection_url, etag.strip('"')),
            headers={'If-None-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        self.assertIn('deleted', records[0])

        # Delete all the things
        resp = self.session.delete(collection_url)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def play_user_shared_bucket_tutorial(self):
        bucket_id = 'bucket-%s' % uuid.uuid4()
        collection_id = 'tasks-%s' % uuid.uuid4()
        collection_url = self.collection_url(bucket_id, collection_id)

        # Create a new bucket and check for permissions
        resp = self.session.put(self.bucket_url(bucket_id))
        self.incr_counter("status-%s" % resp.status_code)
        # In case of concurrent execution, it may have been created already.
        self.assertIn(resp.status_code, (200, 201))
        record = resp.json()
        self.assertIn('write', record['permissions'])

        # Create a new collection and check for permissions
        permissions = {"record:create": ['system.Authenticated']}
        resp = self.session.put(
            re.sub('/records$', '', collection_url),
            data=json.dumps({'permissions': permissions}))
        self.incr_counter("status-%s" % resp.status_code)
        # In case of concurrent execution, it may have been created already.
        self.assertIn(resp.status_code, (200, 201))
        record = resp.json()
        self.assertIn('record:create', record['permissions'])
        self.assertIn('system.Authenticated',
                      record['permissions']['record:create'])

        # Create a new tasks for Alice
        alice_auth = HTTPBasicAuth('token', 'alice-secret-%s' % uuid.uuid4())
        alice_task = build_task()
        resp = self.session.post(
            collection_url,
            data=json.dumps({'data': alice_task}),
            auth=alice_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
        record = resp.json()
        self.assertIn('write', record['permissions'])
        alice_task_id = record['data']['id']

        bob_auth = HTTPBasicAuth('token', 'bob-secret-%s' % uuid.uuid4())

        # Bob has no task yet, he should get a 403.
        resp = self.session.get(collection_url, auth=bob_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 403)

        # Create a new tasks for Bob
        bob_task = build_task()
        resp = self.session.post(
            collection_url,
            data=json.dumps({'data': bob_task}),
            auth=bob_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
        record = resp.json()
        self.assertIn('write', record['permissions'])
        bob_user_id = record['permissions']['write'][0]
        bob_task_id = record['data']['id']

        # Now that he has a task, he should see his.
        resp = self.session.get(collection_url, auth=bob_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], bob_task_id)

        # Share Alice's task with Bob
        resp = self.session.patch(
            self.record_url(alice_task_id, bucket_id, collection_id),
            data=json.dumps({'permissions': {'read': [bob_user_id]}}),
            auth=alice_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertIn('write', record['permissions'])
        alice_task_id = record['data']['id']

        # Check that Bob can access it
        resp = self.session.get(
            self.record_url(alice_task_id, bucket_id, collection_id),
            auth=bob_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)

        # Get mary's userid
        mary_auth = HTTPBasicAuth('token', 'mary-secret-%s' % uuid.uuid4())
        resp = self.session.get(self.api_url(''), auth=mary_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        mary_user_id = record['user']['id']

        # Allow group creation on bucket
        permissions = {"group:create": ['system.Authenticated']}
        resp = self.session.put(
            self.bucket_url(bucket_id),
            data=json.dumps({'permissions': permissions}))
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertIn('group:create', record['permissions'])
        self.assertIn('system.Authenticated',
                      record['permissions']['group:create'])

        # Create Alice's friend group with Bob and Mary
        resp = self.session.put(
            self.group_url(bucket_id, 'alices-friends'),
            data=json.dumps({'data': {'members': [mary_user_id,
                                                  bob_user_id]}}),
            auth=alice_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)

        # Give Alice's task permission for that group
        group_id = self.group_url(bucket_id, 'alices-friends', False)
        resp = self.session.patch(
            self.record_url(alice_task_id, bucket_id, collection_id),
            data=json.dumps({'permissions': {'read': [group_id]}}),
            auth=alice_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertIn(group_id, record['permissions']['read'])

        # Try to access Alice's task with Mary
        resp = self.session.get(
            self.record_url(alice_task_id, bucket_id, collection_id),
            auth=mary_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)

        # Check that Mary's collection_get sees Alice's task
        resp = self.session.get(collection_url, auth=mary_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['id'], alice_task_id)

        # Check that Bob's collection_get sees both his and Alice's tasks
        resp = self.session.get(collection_url, auth=bob_auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 2)
        records_ids = [r['id'] for r in records]
        self.assertIn(alice_task_id, records_ids)
        self.assertIn(bob_task_id, records_ids)

    def check_for_lists(self):
        # List buckets should be forbidden
        resp = self.session.get(
            self.api_url('buckets'))
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
