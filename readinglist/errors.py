import json

from readinglist.utils import Enum

ERRORS = Enum(
    MISSING_AUTH_TOKEN=104,
    INVALID_AUTH_TOKEN=105,
    BADJSON=106,
    INVALID_PARAMETERS=107,
    MISSING_PARAMETERS=108,
    INVALID_POSTED_DATA=109,
    INVALID_RESOURCE_ID=110,
    MISSING_RESOURCE=111,
    FORBIDDEN=121,
    REQUEST_TOO_LARGE=113,
    CLIENT_REACHED_CAPACITY=117,
    UNDEFINED=999,
    BACKEND=201
)


def get_formatted_error(code, errno, error, message=None, info=None):
    result = {
        "code": code,
        "errno": errno,
        "error": error
    }

    if message is not None:
        result['message'] = message

    if info is not None:
        result['info'] = info

    return json.dumps(result)
