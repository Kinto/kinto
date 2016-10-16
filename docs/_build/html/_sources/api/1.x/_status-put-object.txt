HTTP Status Code
----------------

* |status-201|: The object was created
* |status-200|: The object was replaced
* |status-400|: The request body is invalid
* |status-401|: The request is missing authentication headers
* |status-403|: The user is not allowed to perform the operation, or the resource is not accessible
* |status-406|: The client doesn't accept supported responses Content-Type.
* |status-412|: Record was changed or deleted since value in ``If-Match`` header.
* |status-415|: The client request was not sent with a correct Content-Type.
