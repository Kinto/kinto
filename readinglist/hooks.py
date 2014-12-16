from flask import g
from flask import current_app as app

from ua_parser.user_agent_parser import Parse as ua_parse

from readinglist import schemas


def __filter_by_author(request, lookup):
    lookup['author'] = g.get("auth_value")


def __track_device(request, payload):
    try:
        article_id = request.view_args['_id']
    except (AttributeError, KeyError):
        return

    db = app.data.driver.session
    article = db.query(schemas.Article).filter_by(id=article_id).first()
    if not article:
        return

    try:
        useragent = ua_parse(request.headers['User-Agent'])
        device = ('{0}-{1}-{2}'.format(useragent['device']['family'],
                                       useragent['os']['family'],
                                       useragent['user_agent']['family']))
    except KeyError:
        device = 'Unknown'

    existing = db.query(schemas.ArticleDevice)\
                 .filter_by(article=article, device=device)\
                 .first()
    if not existing:
        db.add(schemas.ArticleDevice(article=article, device=device, read=0))
        db.commit()


def setup(app):
    app.on_pre_GET_articles += __filter_by_author
    app.on_pre_GET_articles += __track_device
