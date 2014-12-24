from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext import hybrid
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime)

Base = declarative_base()


class CommonColumns(Base):
    __abstract__ = True
    _created = Column(DateTime, default=func.now())
    _updated = Column(DateTime, default=func.now(), onupdate=func.now())

    @classmethod
    def eve_schema(cls, name):
        return cls._eve_schema[name]

    @hybrid_property
    def _id(self):
        """
        Eve backward compatibility
        """
        return self.id

    def jsonify(self):
        """
        Used to dump related objects to json
        """
        relationships = inspect(self.__class__).relationships.keys()
        mapper = inspect(self)
        attrs = [a.key for a in mapper.attrs
                 if a.key not in relationships and
                 a.key not in mapper.expired_attributes]
        model_descriptors = inspect(self.__class__).all_orm_descriptors
        attrs += [a.__name__ for a in model_descriptors
                  if a.extension_type is hybrid.HYBRID_PROPERTY]
        return dict([(c, getattr(self, c, None)) for c in attrs])


class Device(CommonColumns):
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner = Column(String(256))
    name = Column(String(256), unique=True)

    __tablename__ = 'device'

    @classmethod
    def eve_schema(cls, name):
        schema = super(Device, cls).eve_schema(name)
        schema['schema']['name']['minlength'] = 2
        return schema


class Article(CommonColumns):
    id = Column(Integer, primary_key=True, autoincrement=True)
    author = Column(String(256))
    title = Column(String(512), nullable=False)
    url = Column(String(512), unique=True, nullable=False)
    status = relationship("ArticleStatus", backref="article")

    __tablename__ = 'article'

    @classmethod
    def eve_schema(cls, name):
        schema = super(Article, cls).eve_schema(name)
        schema['schema']['url']['minlength'] = 6
        schema['schema']['title']['minlength'] = 1
        schema['schema']['status']['data_relation']['resource'] = 'article_status'
        return schema


class ArticleStatus(CommonColumns):
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('device.id'), nullable=False)
    device = relationship("Device", backref="statuses")
    read = Column(Integer, default=0, nullable=False)

    __tablename__ = 'article_status'

    @classmethod
    def eve_schema(cls, name):
        schema = super(ArticleStatus, cls).eve_schema(name)
        schema['schema']['article_id']['data_relation']['resource'] = 'articles'
        schema['schema']['device_id']['data_relation']['resource'] = 'devices'
        return schema
