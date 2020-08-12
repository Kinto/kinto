import json


def record_size(record):
    # We cannot use ultrajson here, since the `separator` option is not available.
    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return len(canonical_json)
