import json
from typing import List

from sqlalchemy import Column, Integer, Text, LargeBinary, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from tornado.httpclient import HTTPResponse
from tornado.httputil import HTTPHeaders


Base = declarative_base()


class Workspace(Base):
    __tablename__ = 'workspaces'

    id = Column(Integer, primary_key=True)
    name = Column(Text)

    def update_labels(self, session, labels: List[str]):
        self.update_model_by_field(session, Label, 'text', labels)

    def update_urls(self, session, urls: List[str]):
        self.update_model_by_field(session, Page, 'url', urls)

    def update_model_by_field(
            self, session, model: Base, field: str, values: List[str]):
        values = set(values)
        obj_by_value = {getattr(obj, field): obj for obj in
                        session.query(model).filter(model.workspace == self.id)}
        for value in set(obj_by_value) - values:
            session.delete(obj_by_value[value])
        for value in values - set(obj_by_value):
            session.add(model(workspace=self.id, **{field: value}))


class Page(Base):
    __tablename__ = 'pages'

    id = Column(Integer, primary_key=True)
    workspace = Column(ForeignKey(Workspace.id))
    url = Column(Text)

    # TODO - workspace and url are unique together


class Label(Base):
    __tablename__ = 'labels'

    id = Column(Integer, primary_key=True)
    workspace = Column(ForeignKey(Workspace.id))
    text = Column(Text)

    # TODO - workspace and text are unique together


class ElementLabel(Base):
    __tablename__ = 'element_labels'

    id = Column(Integer, primary_key=True)
    page = Column(ForeignKey(Page.id))
    selector = Column(Text)
    label = Column(ForeignKey(Label.id))

    # TODO - page and selector are unique together


class Response(Base):
    __tablename__ = 'responses'

    id = Column(Integer, primary_key=True)
    url = Column(Text, unique=True)
    _headers = Column(Text)
    body = Column(LargeBinary)
    # TODO - link to page? Or this will change anyway

    def __init__(self, *, url: str, headers: HTTPHeaders, body: bytes):
        self.url = url
        self._headers = dump_headers(headers)
        self.body = body

    @property
    def headers(self):
        return load_headers(self._headers)

    def __repr__(self):
        return '<Response "{}">'.format(self.url)


def dump_headers(headers: HTTPHeaders) -> str:
    return json.dumps(list(headers.get_all()))


def load_headers(data: str) -> HTTPHeaders:
    headers = HTTPHeaders()
    for k, v in json.loads(data):
        headers.add(k, v)
    return headers


def get_response(session, url: str) -> Response:
    return session.query(Response).filter_by(url=url).one_or_none()


def save_response(session, url: str, response: HTTPResponse):
    session.add(Response(
        url=url,
        headers=response.headers,
        body=response.body))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
