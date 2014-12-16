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
        attrs = [a.key for a in mapper.attrs if \
            a.key not in relationships \
            and not a.key in mapper.expired_attributes]
        model_descriptors = inspect(self.__class__).all_orm_descriptors
        attrs += [a.__name__ for a in model_descriptors if \
            a.extension_type is hybrid.HYBRID_PROPERTY]
        return dict([(c, getattr(self, c, None)) for c in attrs])


class Account(Base):
    __tablename__ = 'account'
    id = Column(Integer, primary_key=True, autoincrement=True)


class Article(CommonColumns):
    __tablename__ = 'article'
    id = Column(Integer, primary_key=True, autoincrement=True)
    author = Column(Integer, ForeignKey('account.id'))
    title = Column(String(512), nullable=False)
    url = Column(String(512), unique=True, nullable=False)
    devices = relationship("ArticleDevice", backref="article")


class ArticleDevice(CommonColumns):
    __tablename__ = 'article_device'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device = Column(String(128), nullable=False)
    article_id = Column(Integer, ForeignKey('article.id'), nullable=False)

    read = Column(Integer, default=0, nullable=False)
