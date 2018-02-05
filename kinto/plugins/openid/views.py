import hashlib
import urllib.parse
import os

import requests
from pyramid import httpexceptions

from kinto.core import Service


state = Service(name='openid_state',
                path='/openid/state',
                description='')
@state.get()
def get_state(request):
    state = hashlib.sha256(os.urandom(1024)).hexdigest()
    callback = request.GET.get("callback")
    request.registry.cache.set("openid:state:" + state, callback, ttl=3600)
    return {
        'state': state
    }


code = Service(name='openid_token',
               path='/openid/token',
               description='')

@code.get()
def get_code(request):
    code = request.GET.get("code")
    state = request.GET.get("state")

    callback = request.registry.cache.get("openid:state:" + state)
    if callback is None:
        # XXX: invalid state: raise 400
        return {}

    request.registry.cache.delete("openid:state:" + state)

    client_id = request.registry.settings["oidc.client_id"]
    client_secret = request.registry.settings["oidc.client_secret"]

    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': request.route_url('openid_token') + '?',
        'grant_type': 'authorization_code'
    }

    resp = requests.post("https://www.googleapis.com/oauth2/v4/token", data=data)
    if resp.status_code != 200:
        # XXX: redirect with #&error=<message for ui>
        return resp.json()

    redirect = callback + urllib.parse.quote(resp.text)
    raise httpexceptions.HTTPTemporaryRedirect(redirect)
