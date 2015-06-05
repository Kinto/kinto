from functools import wraps

import requests
import six
from requests.exceptions import RequestException

from cliquet import logger
from cliquet.storage import (
    StorageBase, exceptions, Filter,
    DEFAULT_ID_FIELD, DEFAULT_MODIFIED_FIELD, DEFAULT_DELETED_FIELD)
from cliquet.storage.memory import apply_sorting, get_unicity_rules
from cliquet.utils import json, COMPARISON


API_PREFIX = "/v0"


FILTERS = {
    COMPARISON.LT: 'lt_',
    COMPARISON.MIN: 'min_',
    COMPARISON.MAX: 'max_',
    COMPARISON.NOT: 'not_',
    COMPARISON.EQ: '',
    COMPARISON.GT: 'gt_',
}


def wrap_http_error(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RequestException as e:
            status_code = body = None
            if e.response is not None:
                status_code = e.response.status_code
                try:
                    body = e.response.json()
                except ValueError:
                    body = e.response.content

            if status_code == 404:
                object_id = '?'
                raise exceptions.RecordNotFoundError(object_id)
            logger.debug(body)
            raise exceptions.BackendError(original=e)
    return wrapped


class CloudStorage(StorageBase):
    """Storage backend implementation using `Kinto <http://kinto.rtfd.org>`_.

    Enable in configuration::

        cliquet.storage_backend = cliquet.storage.cloud_storage

    Instance location URI should be customized::

        cliquet.storage_url = https://cloud-storage.services.mozilla.com

    A first implementation of this service was published as
    :rtd:`Kinto <kinto>`. In order to run an instance locally, run this
    command:

    ::

        make runkinto

    .. note::

        In order to avoid double checking of OAuth tokens, the Kinto service
        and the application can share the same cache (``cliquet.cache_url``).
    """

    # XXX: todo: use parent_id for bucket
    collection_url = "/collections/{0}/records"
    record_url = "/collections/{0}/records/{1}"

    def __init__(self, server_url, *args, **kwargs):
        super(CloudStorage, self).__init__(*args, **kwargs)
        self._client = requests.Session()
        self.server_url = server_url

    def _build_url(self, resource):
        return self.server_url + API_PREFIX + resource

    def _headers(self, auth=None):
        """Build list of headers to be sent to remote server.
        """
        headers = {
            'Content-Type': 'application/json',
        }
        if auth:
            headers['Authorization'] = auth
        return headers

    def initialize_schema(self):
        # Nothing to do.
        pass

    @wrap_http_error
    def flush(self, auth=None):
        url = self._build_url("/__flush__")
        resp = self._client.post(url, headers=self._headers(auth))
        resp.raise_for_status()

    @wrap_http_error
    def collection_timestamp(self, collection_id, parent_id, auth=None):
        url = self._build_url(self.collection_url.format(collection_id))
        resp = self._client.head(url, headers=self._headers(auth))
        resp.raise_for_status()
        return int(resp.headers['Last-Modified'])

    def check_unicity(self, collection_id, parent_id, record, unique_fields,
                      id_field, auth):
        rules = get_unicity_rules(collection_id, parent_id, record,
                                  unique_fields=unique_fields,
                                  id_field=id_field)
        for rule in rules:
            new_rule = []
            for filter_ in rule:
                value = filter_.value
                if isinstance(value, six.string_types):
                    filter_ = Filter(filter_.field, "'%s'" % filter_.value,
                                     filter_.operator)
                new_rule.append(filter_)

            result, count = self.get_all(collection_id, parent_id, new_rule,
                                         auth=auth)
            if count != 0:
                raise exceptions.UnicityError(rule[0].field,
                                              result[0])

    @wrap_http_error
    def create(self, collection_id, parent_id, record, id_generator=None,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        id_generator = id_generator or self.id_generator
        if unique_fields:
            self.check_unicity(collection_id, parent_id, record,
                               unique_fields, id_field, auth)
        object_id = id_generator()
        url = self._build_url(self.record_url.format(collection_id,
                                                     object_id))
        resp = self._client.put(url,
                                data=json.dumps(record),
                                headers=self._headers(auth))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def get(self, collection_id, parent_id, object_id,
            id_field=DEFAULT_ID_FIELD,
            modified_field=DEFAULT_MODIFIED_FIELD,
            auth=None):
        url = self._build_url(self.record_url.format(collection_id,
                                                     object_id))
        resp = self._client.get(url, headers=self._headers(auth))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def update(self, collection_id, parent_id, object_id, record,
               unique_fields=None, id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               auth=None):
        if unique_fields:
            self.check_unicity(collection_id, parent_id, record,
                               unique_fields, id_field, auth)
        url = self._build_url(self.record_url.format(collection_id,
                                                     object_id))
        try:
            self.get(collection_id, parent_id, object_id,
                     id_field=id_field, auth=auth)
        except exceptions.RecordNotFoundError:
            resp = self._client.put(url,
                                    data=json.dumps(record),
                                    headers=self._headers(auth))
        else:
            if id_field in record:
                del record[id_field]
            resp = self._client.patch(url,
                                      data=json.dumps(record),
                                      headers=self._headers(auth))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def delete(self, collection_id, parent_id, object_id,
               id_field=DEFAULT_ID_FIELD,
               modified_field=DEFAULT_MODIFIED_FIELD,
               deleted_field=DEFAULT_DELETED_FIELD,
               auth=None):
        url = self._build_url(self.record_url.format(collection_id,
                                                     object_id))
        resp = self._client.delete(url, headers=self._headers(auth))
        resp.raise_for_status()
        return resp.json()

    @wrap_http_error
    def delete_all(self, collection_id, parent_id, filters=None,
                   id_field=DEFAULT_ID_FIELD,
                   modified_field=DEFAULT_MODIFIED_FIELD,
                   deleted_field=DEFAULT_DELETED_FIELD,
                   auth=None):
        url = self._build_url(self.collection_url.format(collection_id))
        params = []
        if filters:
            params += [("%s%s" % (FILTERS[op], k), v) for k, v, op in filters]
        resp = self._client.delete(url,
                                   params=params,
                                   headers=self._headers(auth))
        resp.raise_for_status()

    def _filters_as_params(self, filters):
        params = []
        for k, v, op in filters:
            if isinstance(v, six.string_types):
                # Literals '\' should be preserved in querystring
                v = v.replace("\\", "\\\\")
            params.append(("%s%s" % (FILTERS[op], k), v))
        return params

    def _params_as_querystring(self, params):
        return '&'.join(["%s=%s" % (p, v) for p, v in params])

    @wrap_http_error
    def get_all(self, collection_id, parent_id, filters=None, sorting=None,
                pagination_rules=None, limit=None, include_deleted=False,
                id_field=DEFAULT_ID_FIELD,
                modified_field=DEFAULT_MODIFIED_FIELD,
                deleted_field=DEFAULT_DELETED_FIELD,
                auth=None):
        url = self.collection_url.format(collection_id)

        params = []

        sort_fields = []
        if sorting:
            for field, direction in sorting:
                prefix = '-' if direction < 0 else ''
                sort_fields.append(prefix + field)

        if sort_fields:
            params += [("_sort", ','.join(sort_fields))]

        if filters:
            params += self._filters_as_params(filters)

        if limit:
            params.append(("_limit", limit))

        if not pagination_rules:
            resp = self._client.get(self._build_url(url),
                                    params=params,
                                    headers=self._headers(auth))
            resp.raise_for_status()

            count = resp.headers['Total-Records']
            records = resp.json()['items']

        else:
            batch_payload = {'defaults': {'body': {}}, 'requests': []}

            querystring = self._params_as_querystring(params)
            batch_payload['requests'].append({
                'method': 'HEAD',
                'path': url + '?%s' % querystring,
            })

            for filters in pagination_rules:
                params_ = list(params)
                params_ += self._filters_as_params(filters)
                querystring = self._params_as_querystring(params_)
                batch_payload['requests'].append({
                    'path': url + '?%s' % querystring,
                })

            resp = self._client.post(self._build_url('/batch'),
                                     data=json.dumps(batch_payload),
                                     headers=self._headers(auth))
            resp.raise_for_status()
            batch_responses = resp.json()['responses']

            if any([r['status'] >= 400 for r in batch_responses]):
                http_error = requests.HTTPError('Batch error', response=resp)
                raise exceptions.BackendError(original=http_error)

            count = batch_responses[0]['headers']['Total-Records']
            records = {}
            for batch_response in batch_responses[1:]:
                for record in batch_response['body']['items']:
                    records[record[id_field]] = record

            if sorting:
                records = apply_sorting(records.values(), sorting)[:limit]

        return records, int(count)


def load_from_config(config):
    settings = config.get_settings()
    server_url = settings['cliquet.storage_url']
    return CloudStorage(server_url=server_url)
