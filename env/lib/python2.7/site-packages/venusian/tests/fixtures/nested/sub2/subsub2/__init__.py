from venusian.tests.fixtures import decorator

@decorator(function=True)
def function(request): # pragma: no cover
    return request
