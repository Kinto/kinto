HTTP Status Code
----------------

* ``200 OK``: The object was modified
* ``400 Bad Request``: The request body is invalid, or a read-only field was
  modified
* ``401 Unauthorized``: The request is missing authentication headers
* ``403 Forbidden``: The user is not allowed to perform the operation, or the
  resource is not accessible
* ``406 Not Acceptable``: The client doesn't accept supported responses Content-Type.
* ``409 Conflict``: If modifying this object violates a field unicity constraint
* ``412 Precondition Failed``: Record changed since value in ``If-Match`` header
* ``415 Unsupported Media Type``: The client request was not sent with a correct Content-Type.
