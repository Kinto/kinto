
HTTP Status Code
----------------

* ``201 Created``: The object was created
* ``200 OK``: The object was replaced
* ``400 Bad Request``: The request body is invalid
* ``401 Unauthorized``: The request is missing authentication headers
* ``403 Forbidden``: The user is not allowed to perform the operation, or the
  resource is not accessible
* ``406 Not Acceptable``: The client doesn't accept supported responses Content-Type.
* ``409 Conflict``: If replacing this object violates a field unicity constraint
* ``412 Precondition Failed``: Record was changed or deleted since value
  in ``If-Match`` header.
* ``415 Unsupported Media Type``: The client request was not sent with a correct Content-Type.
