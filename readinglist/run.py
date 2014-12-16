import os

from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap

from readinglist import hooks, schemas, views


here = os.path.abspath(os.path.dirname(__file__))
settings_file = os.path.join(here, 'settings.py')

app = Eve(validator=ValidatorSQL, data=SQL, settings=settings_file)

hooks.setup(app)

app.register_blueprint(views.main)

# bind SQLAlchemy
db = app.data.driver
schemas.Base.metadata.bind = db.engine
db.Model = schemas.Base
db.create_all()

# Activate docs
Bootstrap(app)
docs_prefix = '/%s/docs' % app.config['URL_PREFIX']
app.register_blueprint(eve_docs, url_prefix=docs_prefix)


if __name__ == '__main__':
    app.run()
