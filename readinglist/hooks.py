from flask import g
#from flask import current_app as app

#from ua_parser.user_agent_parser import Parse as ua_parse

#from readinglist import schemas


def __filter_by_author(request, lookup):
    lookup['author'] = g.get("auth_value")


def __filter_by_owner(request, lookup):
    lookup['owner'] = g.get("auth_value")


def __preprocess_article_status(request):
    try:
        article_id = int(request.view_args['article_id'])
    except (AttributeError, KeyError, ValueError):
        return
    request.get_data()
    request.json[u'article_id'] = article_id


def setup(app):
    app.on_pre_GET_articles += __filter_by_author
    app.on_pre_GET_devices += __filter_by_owner
    app.on_pre_POST_article_status += __preprocess_article_status
