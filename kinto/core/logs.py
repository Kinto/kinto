def log_context(request, **kwargs):
    """Bind information to the current request summary log.
    """
    try:
        request._log_context.update(**kwargs)
    except AttributeError:
        request._log_context = kwargs
    return request._log_context
