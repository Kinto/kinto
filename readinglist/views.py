"""
Blueprint for reading list endpoints not provided by python Eve.
"""
import uuid

from flask import request, jsonify, Blueprint, session, abort

from readinglist import exceptions
from readinglist import auth


STORAGE_BACKEND = {
    'state': {}
}


fxa = Blueprint("fxa", __name__)


@fxa.route("/fxa-oauth/params")
def fxa_oauth_params():
    """Create session and provide the OAuth parameters to the client.
    """
    from flask import current_app as app

    # Persist session id with cookies
    session.setdefault("session_id", uuid.uuid4().hex)
    session_id = session["session_id"]

    # Store arbitrary string (state), checked when return from login page
    state = uuid.uuid4().hex
    STORAGE_BACKEND['state'][session_id] = state

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


@fxa.route("/fxa-oauth/token")
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
    code = request.args.get("code")
    state = request.args.get("state")
    if not (code and state):
        raise exceptions.UsageError(message="Missing code or state")

    # Compare previously stored state
    stored_state = STORAGE_BACKEND['state'].pop(session_id, None)
    if stored_state != state:
        raise exceptions.UsageError(message="Invalid state")

    # Trade the OAuth code for a longer-lived token
    try:
        token = auth.fxa_trade_token(
            oauth_uri=app.config["FXA_OAUTH_URI"],
            client_id=app.config["FXA_CLIENT_ID"],
            client_secret=app.config["FXA_CLIENT_SECRET"],
            code=code)
    except auth.OAuth2Error:
        abort(503)

    data = {
        'token': token,
    }
    response = jsonify(**data)
    response.headers['Session-Id'] = session_id
    return response
