"""
Blueprint for reading list endpoints not provided by python Eve.
"""
import uuid

from flask import request, jsonify, Blueprint, redirect, session, abort

from readinglist import API_VERSION, exceptions
from readinglist import auth


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


@main.route("/%s/fxa-oauth/tokens" % API_VERSION, methods=["POST"])
def fxa_oauth_token():
    from flask import current_app as app

    # Require on-going session
    if "session_id" in session:
        session_id = session["session_id"]
    else:
        session_id = request.headers.get('Session-Id')
    if not session_id:
        abort(401)

    # Initial state and FxA code to trade
    data = request.get_json() or {}
    code = data.get("code")
    state = data.get("state")
    if not (code and state):
        raise exceptions.InvalidUsage(message="Missing code or state")

    # Compare previously stored state
    stored_state = STORAGE_BACKEND['state'][session_id]
    if stored_state != state:
        raise exceptions.InvalidUsage(message="Invalid state")

    # Trade the OAuth code for a durable token
    try:
        token = auth.fxa_trade_token(
            oauth_uri=app.config["FXA_OAUTH_URI"],
            client_id=app.config["FXA_CLIENT_ID"],
            client_secret=app.config["FXA_CLIENT_SECRET"],
            code=code)
    except:
        abort(503)

    # Fetch profile data from FxA account
    try:
        profile = auth.fxa_fetch_profile(
            oauth_uri=app.config["FXA_OAUTH_URI"],
            token=token)
    except:
        abort(503)

    session['username'] = profile['uid']

    data = {
        "profile": profile
    }
    response = jsonify(**data)
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

    stored_next = STORAGE_BACKEND['next'].get(state)
    if not stored_next:
        raise exceptions.InvalidUsage(message="Unknown state")

    return redirect(next)
