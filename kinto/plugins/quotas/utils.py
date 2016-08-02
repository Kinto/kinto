import json


def record_size(record):
    canonical_json = json.dumps(record, sort_keys=True, separators=(',', ':'))
    print(canonical_json)
    return len(canonical_json)
