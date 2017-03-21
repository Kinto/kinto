It supports the same filtering, sorting and pagination capabilities as GET.

If the number of records to be deleted exceeds to pagination limit, a response
header ``Next-Page`` will be provided.

If the ``If-Match: "<timestamp>"`` request header is provided, and if the list
has changed meanwhile, a |status-412| error is returned.
