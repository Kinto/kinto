def fxa_conf(request, name):
    key = 'fxa-oauth.' + name
    return request.registry.settings[key]
