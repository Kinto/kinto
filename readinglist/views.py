"""
Blueprint for reading list endpoints not provided by python Eve.
"""
from flask import Blueprint, redirect

import settings


main = Blueprint("main", __name__)


@main.route("/")
def home():
    return redirect('%s' % settings.URL_PREFIX)
