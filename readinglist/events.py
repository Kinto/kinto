def __filter_by_author(request, lookup):
    username = request.authorization['username']
    lookup['author'] = username


def bind(app):
    app.on_pre_GET_article += __filter_by_author
