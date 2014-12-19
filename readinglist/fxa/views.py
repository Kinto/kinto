"""
Blueprint for Firefox Account authentication views.
"""
import uuid

from flask import request, jsonify, Blueprint, session, abort, redirect

from readinglist import exceptions
from readinglist.fxa import OAuth2Error, trade_code


class FxABlueprint(Blueprint):
    def register(self, app, *args, **kwargs):
        super(FxABlueprint, self).register(app, *args, **kwargs)
        self.client_id = app.config['FXA_CLIENT_ID']
        self.client_secret = app.config['FXA_CLIENT_SECRET']
        self.redirect_uri = app.config['FXA_REDIRECT_URI']
        self.profile_uri = app.config['FXA_PROFILE_URI']
        self.oauth_uri = app.config['FXA_OAUTH_URI']
        self.scope = app.config['FXA_SCOPE']


fxa = FxABlueprint("fxa", __name__)


def persist_state():
    """Persist arbitrary string in session.
    It will be compared when return from login page on OAuth server.
    """
    state = uuid.uuid4().hex
    session['state'] = state
    return state


@fxa.route("/login")
def fxa_oauth_login():
    """Helper to redirect client towards FxA login form.
    """
    state = persist_state()
    form_url = ('{oauth_uri}/authorization?action=signin'
                '&client_id={client_id}&state={state}&scope={scope}')
    form_url = form_url.format(oauth_uri=fxa.oauth_uri,
                               client_id=fxa.client_id,
                               state=state,
                               scope=fxa.scope)
    return redirect(form_url)


@fxa.route("/params")
def fxa_oauth_params():
    """Create session and provide the OAuth parameters to the client.
    """
    state = persist_state()
    data = {
        "client_id": fxa.client_id,
        "redirect_uri": fxa.redirect_uri,
        "profile_uri": fxa.profile_uri,
        "oauth_uri": fxa.oauth_uri,
        "scope": fxa.scope,
        "state": state
    }
    response = jsonify(**data)
    return response


@fxa.route("/token")
def fxa_oauth_token():
    """Return OAuth token from authorization code.
    """
    # Require on-going session
    try:
        stored_state = session.pop('state')
    except KeyError:
        abort(401)

    # OAuth server provided state and code through redirection
    code = request.args.get("code")
    state = request.args.get("state")
    if not (code and state):
        raise exceptions.UsageError(message="Missing code or state")

    # Compare with previously persisted state
    if stored_state != state:
        raise exceptions.UsageError(message="Invalid state")

    # Trade the OAuth code for a longer-lived token
    try:
        token = trade_code(oauth_uri=fxa.oauth_uri,
                           client_id=fxa.client_id,
                           client_secret=fxa.client_secret,
                           code=code)
    except OAuth2Error:
        abort(503)

    data = {
        'token': token,
    }
    response = jsonify(**data)
    return response
