#!/usr/bin/env python
import argparse
import json
import logging
import os
import tempfile
from typing import Dict
import zipfile

from sqlalchemy import create_engine
import tornado.ioloop
from tornado.web import Application, RequestHandler, URLSpec

from config import Session, ROOT, STATIC_ROOT
from models import Base, Workspace, Label, Page, ElementLabel
from offline import save_page_for_offline
from proxy import ProxyHandler


class MainHandler(RequestHandler):
    def get(self):
        self.render(
            'templates/main.html',
            urls={
                'ws_list': self.reverse_url('ws_list'),
                'label': self.reverse_url('label'),
                'ws_export': self.reverse_url_one_arg('ws_export'),
                'proxy': self.reverse_url_one_arg('proxy'),
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
        labeled = get_labeled(session, ws)
        ws_data = {
            'id': ws.id,
            'name': ws.name,
            'labels': [label.text for label in
                       session.query(Label).filter_by(workspace=ws.id)],
            'urls': [page.url for page in
                     session.query(Page).filter_by(workspace=ws.id)],
            'labeled': labeled,
        }
        self.write(ws_data)


def get_labeled(session: Session, ws: Workspace) -> Dict:
    labeled = {}
    for element_label, page_url, label_text in (
            session.query(ElementLabel, Page.url, Label.text).join(Page)
                    .filter(Page.workspace == ws.id)
                    .all()):
        labeled.setdefault(page_url, {})[element_label.selector] = {
            'selector': element_label.selector,
            'text': label_text,
        }
    return labeled


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
        labeled = get_labeled(session, ws)
        pages = list(session.query(Page).filter_by(workspace=ws.id))
        ws_data = {
            'id': ws.id,
            'name': ws.name,
            'pages': [
                {'id': page.id,
                 'url': page.url,
                 'labeled': {
                     selector: label['text']
                     for selector, label in labeled.get(page.url, {}).items()},
                 } for page in pages],
        }
        with tempfile.NamedTemporaryFile('wb', delete=False) as tempf:
            with zipfile.ZipFile(tempf, mode='w') as archive:
                archive.writestr('meta.json', json.dumps(ws_data, indent=True))
                for page in pages:
                    save_page_for_offline(archive, session, page)
        try:
            with open(tempf.name, 'rb') as f:
                contents = f.read()
        finally:
            os.unlink(tempf.name)
        self.set_header('Content-Disposition',
                        'attachment; filename="workspace_{}.zip"'.format(ws.id))
        self.set_header('Content-Type', 'application/zip')
        self.write(contents)


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
         URLSpec(r'/proxy/(\d+)/', ProxyHandler, name='proxy'),
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
