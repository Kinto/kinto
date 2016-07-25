
HTTP Status Code
----------------

* ``200 OK``: The object was deleted
* ``401 Unauthorized``: The request is missing authentication headers
* ``403 Forbidden``: The user is not allowed to perform the operation, or the
  resource is not accessible
* ``406 Not Acceptable``: The client doesn't accept supported responses Content-Type.
* ``412 Precondition Failed``: Record changed since value in ``If-Match`` header
