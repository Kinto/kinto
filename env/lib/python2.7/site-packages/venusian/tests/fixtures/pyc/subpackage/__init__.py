from venusian.tests.fixtures import decorator

@decorator(function=True)
def pkgfunction(request): # pragma: no cover
    return request

