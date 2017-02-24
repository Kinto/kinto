import json
import re
import unittest
import mock

from pyramid import testing

from kinto import main as kinto_main
from kinto.core.testing import get_user_headers

from .. import support
from .test_history import HistoryWebTest


class HistoryAtViewTest(HistoryWebTest):

    def setUp(self):
        self.bucket_uri = '/buckets/test'
        self.app.put(self.bucket_uri, headers=self.headers)

        self.collection_uri = self.bucket_uri + '/collections/col'
        resp = self.app.put(self.collection_uri, headers=self.headers)
        self.collection = resp.json['data']

        self.group_uri = self.bucket_uri + '/groups/grp'
        body = {'data': {'members': ['elle']}}
        resp = self.app.put_json(self.group_uri, body, headers=self.headers)
        self.group = resp.json['data']

        self.record_uri = '/buckets/test/collections/col/records/rec'
        body = {'data': {'foo': 42}}
        resp = self.app.put_json(self.record_uri, body, headers=self.headers)
        self.record = resp.json['data']

    def build_version_object_uri(self, object_url):
        return object_url + '/version'

    def test_version_doesnt_crash_on_wrong_integer(self):
        self.app.get('/buckets/version/toto', status=404)

    def test_version_doesnt_crash_when_bucket_is_missing_from_the_uri(self):
        self.app.get('/undefined/version/1487870672412', status=404)

    def test_we_can_get_a_bucket_at_a_certain_time(self):
        # Create a record
        resp = self.app.put(self.bucket_uri, headers=self.headers)
        bucket_after_creation = resp.json['data']
        last_modified_after_creation = bucket_after_creation.get('last_modified')

        # Update the bucket
        resp = self.app.patch_json(self.bucket_uri, {'data': {'bar': 21}}, headers=self.headers)
        bucket_after_update = resp.json['data']
        last_modified_after_update = bucket_after_update.get('last_modified')

        # Look at its version 1, 2 and 3
        bucket_version_uri = self.build_version_object_uri(self.bucket_uri)

        # At after creation
        resp = self.app.get('{}/{}'.format(bucket_version_uri, last_modified_after_creation),
                            headers=self.headers)
        bucket = resp.json['data']
        assert bucket == bucket_after_creation

        # At after creation
        resp = self.app.get('{}/{}'.format(bucket_version_uri, last_modified_after_update),
                            headers=self.headers)
        bucket = resp.json['data']
        assert bucket == bucket_after_update

        # Delete the bucket
        resp = self.app.delete(self.bucket_uri, headers=self.headers)

        # After delete we have a 404 because the history has been deleted with the bucket.
        self.app.get('{}/{}'.format(bucket_version_uri, last_modified_after_update),
                     headers=self.headers, status=404)

    def test_we_can_get_a_collection_at_a_certain_time(self):
        # 1. Create a record
        resp = self.app.put(self.collection_uri, headers=self.headers)
        collection_after_creation = resp.json['data']
        last_modified_after_creation = collection_after_creation.get('last_modified')

        # 2. Update the collection
        resp = self.app.patch_json(self.collection_uri,
                                   {'data': {'bar': 21}},
                                   headers=self.headers)
        collection_after_update = resp.json['data']
        last_modified_after_update = collection_after_update.get('last_modified')

        # 3. Delete the collection
        resp = self.app.delete(self.collection_uri, headers=self.headers)
        collection_after_delete = resp.json['data']
        last_modified_after_delete = collection_after_delete.get('last_modified')

        # 4. Look at its version 1, 2 and 3
        collection_version_uri = self.build_version_object_uri(self.collection_uri)

        # At after creation
        resp = self.app.get('{}/{}'.format(collection_version_uri, last_modified_after_creation),
                            headers=self.headers)
        collection = resp.json['data']
        assert collection == collection_after_creation

        # At after creation
        resp = self.app.get('{}/{}'.format(collection_version_uri, last_modified_after_update),
                            headers=self.headers)
        collection = resp.json['data']
        assert collection == collection_after_update

        # At after delete
        resp = self.app.get('{}/{}'.format(collection_version_uri, last_modified_after_delete),
                            headers=self.headers)
        collection = resp.json['data']
        assert collection == collection_after_delete

    def test_we_can_get_a_group_at_a_certain_time(self):
        # 1. Create a record
        resp = self.app.put_json(self.group_uri,
                                 {'data': {'members': ['lui']}},
                                 headers=self.headers)
        group_after_creation = resp.json['data']
        last_modified_after_creation = group_after_creation.get('last_modified')

        # 2. Update the group
        resp = self.app.patch_json(self.group_uri,
                                   {'data': {'members': ['elle', 'lui']}},
                                   headers=self.headers)
        group_after_update = resp.json['data']
        last_modified_after_update = group_after_update.get('last_modified')

        # 3. Delete the group
        resp = self.app.delete(self.group_uri, headers=self.headers)
        group_after_delete = resp.json['data']
        last_modified_after_delete = group_after_delete.get('last_modified')

        # 4. Look at its version 1, 2 and 3
        group_version_uri = self.build_version_object_uri(self.group_uri)

        # At after creation
        resp = self.app.get('{}/{}'.format(group_version_uri, last_modified_after_creation),
                            headers=self.headers)
        group = resp.json['data']
        assert group == group_after_creation

        # At after creation
        resp = self.app.get('{}/{}'.format(group_version_uri, last_modified_after_update),
                            headers=self.headers)
        group = resp.json['data']
        assert group == group_after_update

        # At after delete
        resp = self.app.get('{}/{}'.format(group_version_uri, last_modified_after_delete),
                            headers=self.headers)
        group = resp.json['data']
        assert group == group_after_delete

    def test_we_can_get_a_record_at_a_certain_time(self):
        # 1. Create a record
        body = {'data': {'foo': 42}}
        resp = self.app.put_json(self.record_uri, body, headers=self.headers)
        record_after_creation = resp.json['data']
        last_modified_after_creation = record_after_creation.get('last_modified')

        # 2. Update the record
        resp = self.app.patch_json(self.record_uri, {'data': {'bar': 21}}, headers=self.headers)
        record_after_update = resp.json['data']
        last_modified_after_update = record_after_update.get('last_modified')

        # 3. Delete the record
        resp = self.app.delete(self.record_uri, headers=self.headers)
        record_after_delete = resp.json['data']
        last_modified_after_delete = record_after_delete.get('last_modified')

        # 4. Look at its version 1, 2 and 3
        record_version_uri = self.build_version_object_uri(self.record_uri)

        # At after creation
        resp = self.app.get('{}/{}'.format(record_version_uri, last_modified_after_creation),
                            headers=self.headers)
        record = resp.json['data']
        assert record == record_after_creation

        # At after creation
        resp = self.app.get('{}/{}'.format(record_version_uri, last_modified_after_update),
                            headers=self.headers)
        record = resp.json['data']
        assert record == record_after_update

        # At after delete
        resp = self.app.get('{}/{}'.format(record_version_uri, last_modified_after_delete),
                            headers=self.headers)
        record = resp.json['data']
        assert record == record_after_delete
