"""
Blueprint for reading list endpoints not provided by python Eve.
"""
from flask import Blueprint, redirect


main = Blueprint("main", __name__)


@main.route("/")
def home():
    from readinglist.run import app
    return redirect('%s' % app.config['API_VERSION'])
