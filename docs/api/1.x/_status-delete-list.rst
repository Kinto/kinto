HTTP Status Codes
-----------------

* |status-200|: The objects were deleted
* |status-401|: The request is missing authentication headers
* |status-403|: The user is not allowed to perform the operation, or the resource is not accessible
* |status-405|: This endpoint is not available
* |status-406|: The client doesn't accept supported responses Content-Type
* |status-412|: The list has changed since value in ``If-Match`` header
