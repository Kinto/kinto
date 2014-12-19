import os

import flask
from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap

from readinglist import hooks, schemas, exceptions
from readinglist.fxa import views as fxa_views


here = os.path.abspath(os.path.dirname(__file__))
settings_file = os.path.join(here, 'settings.py')

app = Eve(validator=ValidatorSQL, data=SQL, settings=settings_file)

app.secret_key = app.config['SECRET_KEY']
version_prefix = '/%s' % app.config['API_VERSION']

# Setup events and views
hooks.setup(app)
fxa_prefix = version_prefix + '/fxa-oauth'
app.register_blueprint(fxa_views.fxa, url_prefix=fxa_prefix)

# Activate docs
Bootstrap(app)
docs_prefix = version_prefix + '/docs'
app.register_blueprint(eve_docs, url_prefix=docs_prefix)

# Bind SQLAlchemy
db = app.data.driver
schemas.Base.metadata.bind = db.engine
db.Model = schemas.Base
db.create_all()


# Register errors
@app.errorhandler(exceptions.UsageError)
def handle_invalid_usage(error):
    response = flask.jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

if __name__ == '__main__':
    app.run(port=app.config.get('SERVER_PORT'))
