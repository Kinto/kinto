HTTP Status Codes
-----------------

* |status-200|: The request was processed
* |status-304|: Object did not change since value in ``If-None-Match`` header
* |status-400|: The request header is invalid
* |status-401|: The request is missing authentication headers
* |status-403|: The user is not allowed to perform the operation, or the resource is not accessible
* |status-404|: The object does not exist or was deleted
* |status-406|: The client doesn't accept supported responses Content-Type
* |status-412|: Object changed since value in ``If-Match`` header
