#!/usr/bin/env python
import argparse
import json
import logging
from pathlib import Path
from typing import Dict
from urllib.parse import urlsplit, urljoin, unquote, urlencode

from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, contains_eager
import tornado.ioloop
from tornado.gen import coroutine
from tornado.web import Application, RequestHandler, URLSpec
from tornado.httpclient import AsyncHTTPClient
from w3lib.encoding import http_content_type_encoding

from models import Base, get_response, save_response, Workspace, Label, Page, \
    ElementLabel


logging.basicConfig(format='[%(levelname)s] %(asctime)s %(message)s')
ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / 'static'

Session = sessionmaker()


class MainHandler(RequestHandler):
    def get(self):
        self.render('templates/main.html')


class WorkspaceListHandler(RequestHandler):
    def get(self):
        session = Session()
        self.write({
            'workspaces': [{'id': ws.id, 'name': ws.name}
                           for ws in session.query(Workspace)],
        })

    def post(self):
        session = Session()
        data = json.loads(self.request.body.decode('utf8'))
        if data.get('id'):
            workspace = session.query(Workspace).get(data['id'])
        else:
            workspace = Workspace()
        workspace.name = data['name']
        session.add(workspace)
        session.commit()
        workspace.update_labels(session, data['labels'])
        workspace.update_urls(session, data['urls'])
        session.commit()
        self.write({'id': workspace.id})


class WorkspaceHandler(RequestHandler):
    def get(self, ws_id):
        session = Session()
        ws = session.query(Workspace).get(int(ws_id))
        self.write(workspace_to_json(session, ws))


def workspace_to_json(session: Session, ws: Workspace) -> Dict:
    labeled = {}
    for element_label, page_url, label_text in (
            session.query(ElementLabel, Page.url, Label.text).join(Page)
            .filter(Page.workspace == ws.id)
            .all()):
        labeled.setdefault(page_url, {})[element_label.selector] = {
            'selector': element_label.selector,
            'text': label_text,
        }
    return {
        'id': ws.id,
        'name': ws.name,
        'labels': [label.text for label in
                   session.query(Label).filter_by(workspace=ws.id)],
        'urls': [page.url for page in
                 session.query(Page).filter_by(workspace=ws.id)],
        'labeled': labeled,
    }


class LabelHandler(RequestHandler):
    def post(self):
        session = Session()
        data = json.loads(self.request.body.decode('utf8'))
        ws = session.query(Workspace).get(data['wsId'])
        page = session.query(Page).filter_by(
            workspace=ws.id, url=data['url']).one()
        element_label = session.query(ElementLabel).filter_by(
            page=page.id, selector=data['selector']).one_or_none()
        if data.get('label') is not None:
            label = session.query(Label).filter_by(
                workspace=ws.id, text=data['label']).one()
            if element_label is None:
                element_label = ElementLabel(
                    page=page.id,
                    selector=data['selector'],
                    label=label.id)
            else:
                element_label.label = label.id
            session.add(element_label)
        elif element_label is not None:
            session.delete(element_label)
        session.commit()
        self.write({'ok': True})


class ExportHandler(RequestHandler):
    def get(self, ws_id):
        session = Session()
        ws = session.query(Workspace).get(int(ws_id))
        self.set_header('Content-Disposition',
                        'attachment; filename="{}.json"'.format(ws.name))
        self.write(json.dumps(workspace_to_json(session, ws), indent=True))


class ProxyHandler(RequestHandler):
    @coroutine
    def get(self, path):
        referrer = self.request.headers.get('Referer')
        if self.request.arguments:
            path += '?' + urlencode(
                [(k, v) for k, vs in self.request.arguments.items()
                 for v in vs])

        headers = self.request.headers.copy()
        for field in ['cookie', 'referrer']:
            try: del headers[field]
            except KeyError: pass
        if referrer:
            r_path = unquote(urlsplit(referrer).path.lstrip('/'))
            r_path = fixed_full_url(r_path)
            if is_full(r_path):
                headers['referrer'] = r_path
                if not is_full(path):
                    path = urljoin(r_path, path)
                    # FIXME - do we loose referrer here?
                    self.redirect('/' + path)
                    return

        httpclient = AsyncHTTPClient()
        session = Session()
        response = get_response(session, path)
        if response is None:
            response = yield httpclient.fetch(path, raise_error=False)
            save_response(session, path, response)

        body = response.body
        content_type = response.headers.get('content-type', '')
        html_transformed = False
        if content_type.startswith('text/html'):
            encoding = http_content_type_encoding(content_type)
            body, html_transformed = transform_html(body, encoding)

        self.write(body)
        for k, v in response.headers.get_all():
            if k.lower() not in {'content-length', 'set-cookie'}:
                if html_transformed and k.lower() == 'content-type':
                    # change encoding (always utf8 now)
                    v = 'text/html; charset=UTF-8'
                self.set_header(k, v)
        self.finish()


def transform_html(html: bytes, encoding: str) -> bytes:
    soup = BeautifulSoup(html, 'lxml', from_encoding=encoding)
    body = soup.find('body')
    if not body:
        return html, False

    js_tag = soup.new_tag('script', type='text/javascript')
    injected_js = (Path(STATIC_ROOT) / 'js' / 'injected.js').read_text('utf8')
    js_tag.string = injected_js
    body.append(js_tag)

    css_tag = soup.new_tag('style')
    injected_css = (
        Path(STATIC_ROOT) / 'css' / 'injected.css').read_text('utf8')
    css_tag.string = injected_css
    # TODO - create "head" if none exists
    soup.find('head').append(css_tag)

    return soup.encode(), True


def is_full(url: str) -> bool:
    return url.startswith('http://') or url.startswith('https://')


def fixed_full_url(url: str) -> str:
    # TODO - do it properly, this must be tornado removing slash
    if not is_full(url):
        if url.startswith('http:/'):
            url = 'http://' + url[len('http:/'):]
        if url.startswith('https:/'):
            url = 'https://' + url[len('https:/'):]
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--echo', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    app = Application(
        [URLSpec(r'/', MainHandler, name='main'),
         URLSpec(r'/~wpa/workspace/', WorkspaceListHandler, name='ws_list'),
         URLSpec(r'/~wpa/workspace/(\d+)/', WorkspaceHandler),
         URLSpec(r'/~wpa/label/', LabelHandler, name='label'),
         URLSpec(r'/~wpa/export/(\d+)/', ExportHandler, name='ws_export'),
         URLSpec(r'/(.*)', ProxyHandler, name='proxy'),
        ],
        debug=args.debug,
        static_prefix='/static/',
        static_path=str(STATIC_ROOT),
    )
    engine = create_engine(
        'sqlite:///{}'.format(ROOT / 'db.sqlite'), echo=args.echo)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    app.listen(args.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
