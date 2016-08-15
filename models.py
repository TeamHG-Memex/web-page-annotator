import json

from sqlalchemy import Column, Integer, Text, LargeBinary
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from tornado.httpclient import HTTPResponse
from tornado.httputil import HTTPHeaders


Base = declarative_base()


class Response(Base):
    __tablename__ = 'responses'

    id = Column(Integer, primary_key=True)
    url = Column(Text, unique=True)
    _headers = Column(Text)
    body = Column(LargeBinary)
    # TODO - we will need at least some "page set" field

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
