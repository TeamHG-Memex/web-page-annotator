#!/usr/bin/env python
import argparse
import json
import logging
from pathlib import Path
from urllib.parse import urlencode
from typing import Dict

from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, contains_eager
import tornado.ioloop
from tornado.gen import coroutine
from tornado.web import Application, RequestHandler, URLSpec
from tornado.httpclient import AsyncHTTPClient
from w3lib.encoding import http_content_type_encoding
from w3lib.html import get_base_url

from models import Base, get_response, save_response, Workspace, Label, Page, \
    ElementLabel
from transform_html import remove_scripts_and_proxy, process_css


logging.basicConfig(
    format='[%(levelname)s] %(asctime)s %(message)s', level=logging.INFO)
ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / 'static'

Session = sessionmaker()


class MainHandler(RequestHandler):
    def get(self):
        self.render(
            'templates/main.html',
            urls={
                'ws_list': self.reverse_url('ws_list'),
                'label': self.reverse_url('label'),
                'ws_export': self.reverse_url_one_arg('ws_export'),
                'proxy': self.reverse_url('proxy'),
            },
        )

    def reverse_url_one_arg(self, name):
        return self.reverse_url(name, '0').split('0')[0]


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
        self.set_header('Content-Type', 'text/json')
        self.write(json.dumps(workspace_to_json(session, ws), indent=True))


class ProxyHandler(RequestHandler):
    @coroutine
    def get(self):
        session = Session()
        url = self.get_argument('url')
        referrer = self.get_argument('referer', None)
        page = session.query(Page).filter_by(url=referrer or url).one()

        headers = self.request.headers.copy()
        for field in ['cookie', 'referrer']:
            try:
                del headers[field]
            except KeyError:
                pass
        if referrer:
            headers['referrer'] = referrer

        httpclient = AsyncHTTPClient()
        session = Session()
        response = get_response(session, page, url)
        if response is None:
            response = yield httpclient.fetch(url, raise_error=False)
            save_response(session, page, url, response)

        proxy_url_base = self.reverse_url('proxy')

        def proxy_url(resource_url):
            return '{}?{}'.format(proxy_url_base, urlencode({
                'url': resource_url, 'referer': page.url,
            }))

        body = response.body or b''
        html_transformed = False
        content_type = response.headers.get('content-type', '')
        if content_type.startswith('text/html'):
            encoding = http_content_type_encoding(content_type)
            base_url = get_base_url(body, url, encoding)
            html_transformed = True
            body = transform_html(
                body, encoding=encoding, base_url=base_url, proxy_url=proxy_url)
        elif content_type.startswith('text/css'):
            css_source = body.decode('utf8', 'ignore')
            body = process_css(
                css_source, base_uri=url, proxy_url=proxy_url).encode('utf8')

        self.write(body)
        proxied_headers = {'content-type'}  # TODO - other?
        for k, v in response.headers.get_all():
            if k.lower() in proxied_headers:
                if html_transformed and k.lower() == 'content-type':
                    # change encoding (always utf8 now)
                    v = 'text/html; charset=UTF-8'
                self.set_header(k, v)
        self.finish()


def transform_html(
        html: bytes, encoding: str, base_url: str, proxy_url) -> bytes:
    soup = BeautifulSoup(html, 'lxml', from_encoding=encoding)
    body = soup.find('body')
    if not body:
        return html

    remove_scripts_and_proxy(soup, base_url=base_url, proxy_url=proxy_url)

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

    return soup.encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--echo', action='store_true')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    app = Application(
        [URLSpec(r'/', MainHandler, name='main'),
         URLSpec(r'/workspace/', WorkspaceListHandler, name='ws_list'),
         URLSpec(r'/workspace/(\d+)/', WorkspaceHandler),
         URLSpec(r'/label/', LabelHandler, name='label'),
         URLSpec(r'/export/(\d+)/', ExportHandler, name='ws_export'),
         URLSpec(r'/proxy/', ProxyHandler, name='proxy'),
        ],
        debug=args.debug,
        static_prefix='/static/',
        static_path=str(STATIC_ROOT),
    )
    engine = create_engine(
        'sqlite:///{}'.format(ROOT / 'db.sqlite'), echo=args.echo)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    logging.info('Listening on port {}'.format(args.port))
    app.listen(args.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
