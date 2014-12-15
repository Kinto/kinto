import os

from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap

from readinglist import events, schemas, views


settings_file = os.getenv('READINGLIST_SETTINGS', 'settings.py')
app = Eve(validator=ValidatorSQL, data=SQL, settings=settings_file)

events.bind(app)

app.register_blueprint(views.main)

# bind SQLAlchemy
db = app.data.driver
schemas.Base.metadata.bind = db.engine
db.Model = schemas.Base
db.create_all()

# Activate docs
Bootstrap(app)
app.register_blueprint(eve_docs, url_prefix='/docs')
