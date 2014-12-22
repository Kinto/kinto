import json
from cornice import Service

from readinglist.decorators import exists_or_404


articles = Service(name="articles",
                  path='/articles',
                  description="Collection of articles.")


article = Service(name="article",
                 path='/articles/{record_id}',
                 description="Single article.")


@articles.get()
def get_articles(request):
    """List of articles of user."""
    articles = request.db.get_all('article', '')
    body = {
        '_items': articles
    }
    return body


@articles.post()
def create_article(request):
    """Create article for user."""
    article = json.loads(request.body)
    article = request.db.create('article', '', article)
    return article


@article.get()
@exists_or_404()
def get_article(request):
    """Fetch single article of user."""
    record_id = request.matchdict['record_id']
    article = request.db.get('article', '', record_id)
    return article


@article.patch()
@exists_or_404()
def modify_article(request):
    """Modify article of user."""
    record_id = request.matchdict['record_id']
    article = json.loads(request.body)
    article = request.db.update('article', '', record_id, article)
    return article


@article.delete()
@exists_or_404()
def delete_article(request):
    """Delete article of user."""
    record_id = request.matchdict['record_id']
    article = request.db.delete('article', '', record_id)
    return article
