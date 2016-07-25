HTTP Status Codes
-----------------

* ``200 OK``: The objects were deleted
* ``401 Unauthorized``: The request is missing authentication headers
* ``403 Forbidden``: The user is not allowed to perform the operation, or the
  resource is not accessible
* ``405 Method Not Allowed``: This endpoint is not available
* ``406 Not Acceptable``: The client doesn't accept supported responses Content-Type
* ``412 Precondition Failed``: The list has changed since value in ``If-Match`` header
