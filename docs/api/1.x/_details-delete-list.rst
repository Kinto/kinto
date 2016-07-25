It supports the same filtering capabilities as GET.

If the ``If-Match: "<timestamp>"`` request header is provided, and if the list
has changed meanwhile, a |status-412| error is returned.
