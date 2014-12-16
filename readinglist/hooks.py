from flask import g

def __filter_by_author(request, lookup):
    lookup['author'] = g.get("auth_value")


def setup(app):
    app.on_pre_GET_articles += __filter_by_author
