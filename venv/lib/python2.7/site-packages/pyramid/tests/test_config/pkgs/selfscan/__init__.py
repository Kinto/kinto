from pyramid.view import view_config

@view_config(renderer='string')
def abc(request):
    return 'root'

def main():
    from pyramid.config import Configurator
    c = Configurator()
    c.scan()
    return c
