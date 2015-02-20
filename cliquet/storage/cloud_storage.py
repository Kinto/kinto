import requests

from readinglist.storage import StorageBase, exceptions
from readinglist.utils import classname, json, Enum, COMPARISON, encode_token

API_VERSION = "v0"

FILTERS = Enum(**{
    COMPARISON.LT: 'lt_',
    COMPARISON.MIN: 'min_',
    COMPARISON.MAX: 'max_',
    COMPARISON.NOT: 'not_',
    COMPARISON.EQ: 'eq_',
    COMPARISON.GT: 'gt_',
})


class CloudStorage(StorageBase):

    def __init__(self, *args, **kwargs):
        super(CloudStorage, self).__init__(*args, **kwargs)

        self._client = requests.Session(headers={
            'Content-Type': 'application/json'
        })
        self.server_url = '%s/%s' % (
            kwargs.get('storage.url',
                       'https://cloud-storage.services.mozilla.com'),
            API_VERSION)

    def _build_url(self, resource):
        return "%s%s" % (self.server_url, resource)

    def flush(self):
        url = self._build_url("/collections")
        resp = self._client.delete(url)
        resp.raise_for_status()

    def ping(self):
        url = self._build_url("/__heartbeat__")
        resp = self._client.get(url)
        if resp.status_code == 200:
            return True
        return False

    def collection_timestamp(self, resource, user_id):
        """Return the last timestamp for the resource collection of the user"""
        resource_name = classname(resource)
        url = self._build_url("/collections/%s/records" % resource_name)
        resp = self._client.head(url)
        resp.raise_for_status()
        return int(resp.headers['Last-Modified'])

    def create(self, resource, user_id, record):
        self.check_unicity(resource, user_id, record)
        resource_name = classname(resource)
        url = self._build_url("/collections/%s/records" % resource_name)
        resp = self._client.post(url, body=json.dumps(record))
        resp.raise_for_status()
        return resp.json()

    def get(self, resource, user_id, record_id):
        resource_name = classname(resource)
        url = self._build_url("/collections/%s/records/%s" % (
            resource_name, record_id))
        resp = self._client.get(url)
        if resp.status_code == 404:
            raise exceptions.RecordNotFoundError(record_id)
        resp.raise_for_status()
        return resp.json()

    def update(self, resource, user_id, record_id, record):
        self.check_unicity(resource, user_id, record)

        resource_name = classname(resource)
        url = self._build_url("/collections/%s/records/%s" % (
            resource_name, record_id))
        resp = self._client.patch(url, record)
        resp.raise_for_status()
        return resp.json()

    def delete(self, resource, user_id, record_id):
        resource_name = classname(resource)
        url = self._build_url("/collections/%s/records/%s" % (
            resource_name, record_id))
        resp = self._client.delete(url)
        if resp.status_code == 404:
            raise exceptions.RecordNotFoundError(record_id)
        resp.raise_for_status()
        return resp.json()

    def get_all(self, resource, user_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False):
        resource_name = classname(resource)
        url = self._build_url("/collections/%s" % resource_name)

        sort_fields = []
        for field, direction in sorting:
            value = '-' if direction < 0 else ''
            value += "%s" % field
            sort_fields.append(value)

        params = [("_sort", sort_fields.join(','))]
        params += [("%s%s" % (FILTERS[op], k), v) for k, v, op in filters]
        if limit:
            params.append(("_limit", limit))
        if pagination_rules:
            params.append(("_token", encode_token(pagination_rules)))

        resp = self._client.get(url, params=params)
        count = resp.headers.get('Total-Records')
        records = resp.json()['items']
        return records, count


def load_from_config(config):
    settings = config.registry.settings
    server_url = settings.get('storage.url',
                              'https://cloud-storage.services.mozilla.com')
    return CloudStorage(server_url=server_url)
