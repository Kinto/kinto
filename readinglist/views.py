"""
Blueprint for reading list endpoints not provided by python Eve.
"""
import uuid

from flask import request, jsonify, Blueprint, redirect, session

from readinglist import API_VERSION, exceptions


STORAGE_BACKEND = {
    'next': {},
    'state': {}
}

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return redirect("%s" % API_VERSION)


@main.route("/%s/fxa-oauth/params" % API_VERSION)
def fxa_oauth_params():
    """Create session and provide the OAuth parameters to the client.
    """
    from flask import current_app as app

    # Persist session id with cookies
    session.setdefault("session_id", uuid.uuid4().hex)
    session_id = session["session_id"]

    # Store arbitrary string (state) to be checked after login on Firefox Account
    state = uuid.uuid4().hex
    STORAGE_BACKEND['state'][session_id] = state

    # Store next url to redirect after login on Firefox Account
    next = request.args.get('next')
    if not next:
        raise exceptions.InvalidUsage(message="Missing next parameter")
    STORAGE_BACKEND['next'][state] = next

    # OAuth parameters
    params = {
        "client_id": app.config["FXA_CLIENT_ID"],
        "redirect_uri": app.config["FXA_REDIRECT_URI"],
        "profile_uri": app.config["FXA_PROFILE_URI"],
        "content_uri": app.config["FXA_CONTENT_URI"],
        "oauth_uri": app.config["FXA_OAUTH_URI"],
        "scope": app.config["FXA_SCOPE"],
        "state": state
    }

    response = jsonify(**params)
    response.headers['Session-Id'] = session_id
    return response


@main.route("/%s/fxa-oauth/redirect" % API_VERSION)
def fxa_oauth_redirect():
    """
    Check that returned state matches the one we stored in this session.
    """
    state = request.args.get('state')
    if not state:
        raise exceptions.InvalidUsage(message="Missing state parameter")

    next = STORAGE_BACKEND['next'].get(state)
    if not next:
        raise exceptions.InvalidUsage(message="Unknown state")

    return redirect(next)
