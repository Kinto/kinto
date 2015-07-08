import json
import random
import uuid


def build_task():
    suffix = unicode(uuid.uuid4())
    data = {
        "description": "Task description {0}".format(suffix),
        "status": random.choice(("todo", "doing")),
    }
    return data


class TutorialLoadTestMixin(object):
    def play_full_tutorial(self):
        self.play_user_default_bucket_tutorial()
        self.play_user_shared_bucket_tutorial()

    def play_user_default_bucket_tutorial(self):
        collection_id = 'tasks-%s' % uuid.uuid4()

        # Create a new task
        # 201 created with data and permission.write
        task = build_task()
        resp = self.session.post(
            self.collection_url('default', collection_id),
            data=json.dumps({'data': task}),
            auth=self.auth,
            headers={'Content-Type': 'application/json'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
        record = resp.json()
        self.assertEqual(record['data']['description'], task['description'])
        self.assertEqual(record['data']['status'], task['status'])
        self.assertIn('write', record['permissions'])

        # Create a new one with PUT and If-None-Match: "*"
        task = build_task()
        record_id = unicode(uuid.uuid4())
        resp = self.session.put(
            self.record_url(record_id, 'default', collection_id),
            data=json.dumps({'data': task}),
            auth=self.auth,
            headers={'Content-Type': 'application/json',
                     'If-None-Match': '*'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
        record = resp.json()
        self.assertEqual(record['data']['description'], task['description'])
        self.assertEqual(record['data']['status'], task['status'])
        self.assertIn('write', record['permissions'])

        # Fetch the collection list and see the tasks (save the etag)
        resp = self.session.get(
            self.collection_url('default', collection_id),
            auth=self.auth,
            headers={'Content-Type': 'application/json'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 2)
        etag = resp.headers['ETag']

        # Fetch the collection from the Etag and see nothing new
        url = self.collection_url('default', collection_id)
        resp = self.session.get(url,
                                params={'_since': etag.strip('"')},
                                auth=self.auth,
                                headers={'Content-Type': 'application/json'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 0)

        # Update a task
        resp = self.session.patch(
            self.record_url(record_id, 'default', collection_id),
            data=json.dumps({'data': {'status': 'done'}}),
            auth=self.auth,
            headers={'Content-Type': 'application/json'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()
        self.assertEqual(record['data']['status'], 'done')
        self.assertIn('write', record['permissions'])

        # Try an update with If-Match on the saved ETag and see it fails
        resp = self.session.patch(
            self.record_url(record_id, 'default', collection_id),
            data=json.dumps({'data': {'status': 'done'}}),
            auth=self.auth,
            headers={'Content-Type': 'application/json',
                     'If-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 412)
        self.assertEqual(resp.headers['ETag'],
                         '"%s"' % record['data']['last_modified'])

        # Get the list of records and update the ETag
        resp = self.session.get(
            '%s?_since=%s' % (self.collection_url('default', collection_id),
                              etag.strip('"')),
            auth=self.auth,
            headers={'Content-Type': 'application/json'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        etag = resp.headers['ETag']

        # Try an update with If-Match on the new ETag and see it works
        resp = self.session.patch(
            self.record_url(record_id, 'default', collection_id),
            data=json.dumps({'data': {'status': 'done'}}),
            auth=self.auth,
            headers={'Content-Type': 'application/json',
                     'If-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        record = resp.json()['data']
        # XXX: Should be the ETag header see mozilla-services/cliquet#352
        etag = '"%s"' % record['last_modified']

        # Delete the record with If-Match
        resp = self.session.delete(
            self.record_url(record_id, 'default', collection_id),
            auth=self.auth,
            headers={'Content-Type': 'application/json',
                     'If-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)

        # Try the collection get with the ``_since`` parameter
        resp = self.session.get(
            '%s?_since=%s' % (self.collection_url('default', collection_id),
                              etag.strip('"')),
            auth=self.auth,
            headers={'Content-Type': 'application/json',
                     'If-None-Match': etag})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)
        records = resp.json()['data']
        self.assertEqual(len(records), 1)
        self.assertIn('deleted', records[0])

        # Delete all the things
        resp = self.session.delete(
            self.collection_url('default', collection_id),
            auth=self.auth)
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 200)

    def play_user_shared_bucket_tutorial(self):
        # Create a new bucket and check for permissions

        # Create a new collection and check for permissions

        # Create a new tasks for Alice

        # Create a new tasks for Bob

        # Share Alice's task with Bob

        # Check that Bob can access it

        # Create Alice's friend group with Bob and Mary

        # Give Alice's task permission for that group

        # Try to access Alice's task with Mary

        # Check that Mary's collection_get sees Alice's task

        # Check that Bob's collection_get sees both his and Alice's tasks
        pass
