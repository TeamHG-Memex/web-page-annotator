import json
from typing import List

from sqlalchemy import Column, Integer, Text, LargeBinary, ForeignKey, \
    Boolean, UniqueConstraint
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

    __table_args__ = (
        UniqueConstraint('workspace', 'url', name='_workspace_url'),
    )


class Label(Base):
    __tablename__ = 'labels'

    id = Column(Integer, primary_key=True)
    workspace = Column(ForeignKey(Workspace.id))
    text = Column(Text)

    __table_args__ = (
        UniqueConstraint('workspace', 'text', name='_workspace_text'),
    )


class ElementLabel(Base):
    __tablename__ = 'element_labels'

    id = Column(Integer, primary_key=True)
    page = Column(ForeignKey(Page.id))
    selector = Column(Text)
    label = Column(ForeignKey(Label.id))

    __table_args__ = (
        UniqueConstraint('page', 'selector', name='_page_selector'),
    )


class Response(Base):
    __tablename__ = 'responses'

    id = Column(Integer, primary_key=True)
    url = Column(Text)
    _headers = Column(Text)
    body = Column(LargeBinary)
    page = Column(ForeignKey(Page.id))
    is_main = Column(Boolean)

    __table_args__ = (
        UniqueConstraint('page', 'url', name='_page_url'),
    )

    def __init__(self, *, url: str, page: Page, headers: HTTPHeaders,
                 body: bytes, is_main: bool):
        self.url = url
        self.page = page.id
        self._headers = dump_headers(headers)
        self.body = body
        self.is_main = is_main

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


def get_response(session, page: Page, url: str) -> Response:
    return session.query(Response).filter_by(page=page.id, url=url)\
        .one_or_none()


def save_response(session, page: Page, url: str, response: HTTPResponse,
                  is_main: bool) -> Response:
    response = Response(
        url=url,
        page=page,
        headers=response.headers,
        body=response.body,
        is_main=is_main,
    )
    session.add(response)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    return response
