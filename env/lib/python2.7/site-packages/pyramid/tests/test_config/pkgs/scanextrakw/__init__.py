import venusian

def foo(wrapped):
    def bar(scanner, name, wrapped):
        scanner.config.a = scanner.a
    venusian.attach(wrapped, bar)
    return wrapped

@foo
def hello():
    pass

hello() # appease coverage

