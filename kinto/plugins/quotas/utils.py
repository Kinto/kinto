import copy
import json


def record_size(record):
    canonical_json = json.dumps(record, sort_keys=True, separators=(',', ':'))
    return len(canonical_json)


def strip_stats_keys(record):
    record = copy.deepcopy(record)
    for key in ['collection_count', 'record_count', 'storage_size']:
        if key in record:
            del record[key]
    return record
