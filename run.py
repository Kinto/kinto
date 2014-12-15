from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap

from readinglist import events, schemas


app = Eve(validator=ValidatorSQL, data=SQL)

events.bind(app)

# bind SQLAlchemy
db = app.data.driver
schemas.Base.metadata.bind = db.engine
db.Model = schemas.Base
db.create_all()

# Activate docs
Bootstrap(app)
app.register_blueprint(eve_docs, url_prefix='/docs')


if __name__ == '__main__':
    app.run()
