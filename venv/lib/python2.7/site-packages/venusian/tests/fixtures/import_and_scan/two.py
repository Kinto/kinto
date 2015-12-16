from venusian.tests.fixtures import decorator

@decorator(function=True)
def twofunction(request): # pragma: no cover
    return request
