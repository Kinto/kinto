from eve import Eve
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap


def filter_by_author(request, lookup):
    username = request.authorization['username']
    lookup['_author'] = username


app = Eve()

app.on_pre_GET_article += filter_by_author

# Activate docs
Bootstrap(app)
app.register_blueprint(eve_docs, url_prefix='/docs')


if __name__ == '__main__':
    app.run()
