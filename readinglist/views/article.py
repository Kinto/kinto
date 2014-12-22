import json
from cornice import Service


articles = Service(name="articles",
                  path='/articles',
                  description="Collection of articles.")


article = Service(name="article",
                 path='/articles/{article_id}',
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
def get_article(request):
    """Fetch single article of user."""
    article_id = request.matchdict['article_id']
    article = request.db.get('article', '', article_id)
    return article


@article.patch()
def modify_article(request):
    """Modify article of user."""
    article_id = request.matchdict['article_id']
    article = json.loads(request.body)
    article = request.db.update('article', '', article_id, article)
    return article


@article.delete()
def delete_article(request):
    """Delete article of user."""
    article_id = request.matchdict['article_id']
    article = request.db.delete('article', '', article_id)
    return article
