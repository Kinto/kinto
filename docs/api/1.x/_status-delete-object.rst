HTTP Status Codes
-----------------

* |status-200|: The object was deleted
* |status-401|: The request is missing authentication headers
* |status-403|: The user is not allowed to perform the operation, or the resource is not accessible
* |status-404|: The object does not exist or was already deleted
* |status-406|: The client doesn't accept supported responses Content-Type.
* |status-412|: Record changed since value in ``If-Match`` header
