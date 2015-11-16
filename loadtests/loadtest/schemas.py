import json
import os
import random
import uuid

from . import BaseLoadTest


COLLECTIONS = ('addons', 'certificates', 'gfx', 'plugins')
ACTIONS = ('create_put',)


class SchemaValidationTest(BaseLoadTest):
    def __init__(self, *args, **kwargs):
        super(SchemaValidationTest, self).__init__(*args, **kwargs)
        self._init_collections()

    def _init_collections(self):
        # Create `blocklist` bucket
        bucket = {
            'permissions': {'write': ['system.Authenticated']}
        }
        self.session.put(self.bucket_url('blocklist'),
                         data=json.dumps(bucket),
                         headers={'If-None-Match': '*'})
        for collection in COLLECTIONS:
            self._create_collection(collection)

    def _create_collection(self, name):
        here = os.path.abspath(os.path.dirname(__file__))
        schemafile = os.path.join(here, '..', 'schemas', name + '.json')
        jsonschema = json.load(open(schemafile))
        collection = {
            'data': {'schema': jsonschema}
        }
        self.session.put(self.bucket_url('blocklist') + '/collections/' + name,
                         data=json.dumps(collection),
                         headers={'If-None-Match': '*'})

    def _build_record(self, collection):
        by_collection = {
            'addons': {
                'addonId': 'abc',
                'prefs': [],
                'versionRange': []
            },
            'certificates': {
                'issuerName': '',
                'serialNumber': ''
            },
            'gfx': {
                'os': '',
                'vendor': '',
                'devices': [],
                'feature': '',
                'featureStatus': '',
                'driverVersion': '',
                'driverVersionComparator': ''
            },
            'plugins': {
                'versionRange': [{
                    'minVersion': '',
                    'maxVersion': '',
                    'severity': '0',
                    'vulnerabilityStatus': '',
                    'targetApplication': {
                        'id': '',
                        'minVersion': '',
                        'maxVersion': ''
                    }
                }]
            },
        }
        return by_collection[collection]

    def validate_records(self):
        """
        Main entry.
        """
        collection = os.getenv('VALIDATE_COLLECTION')
        if collection is None:
            collection = random.choice(COLLECTIONS)
        self.incr_counter('collection-%s' % collection)

        action = os.getenv('LOAD_ACTION')
        if action is None:
            action = random.choice(ACTIONS)
        self.incr_counter('action-%s' % action)

        return getattr(self, action)(collection)

    def create_put(self, collection):
        record_id = uuid.uuid4()
        record_url = self.record_url(record_id,
                                     bucket='blocklist',
                                     collection=collection)
        # Check that invalid record fails
        resp = self.session.put(record_url,
                                data=json.dumps({'data': {}}),
                                headers={'If-None-Match': '*'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 400)

        # Create valid record succeeds
        record = self._build_record(collection)
        resp = self.session.put(record_url,
                                data=json.dumps({'data': record}),
                                headers={'If-None-Match': '*'})
        self.incr_counter("status-%s" % resp.status_code)
        self.assertEqual(resp.status_code, 201)
