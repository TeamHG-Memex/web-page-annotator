#!/usr/bin/env python
import os.path
import argparse
from pathlib import Path
from urllib.parse import urlsplit, urljoin, unquote, urlencode

from bs4 import BeautifulSoup
import tornado.ioloop
from tornado import web, gen
from tornado.httpclient import AsyncHTTPClient


ROOT = os.path.dirname(__file__)
STATIC_ROOT = os.path.join(ROOT, 'static')


class MainHandler(web.RequestHandler):
    def get(self):
        self.render('templates/main.html')


class ProxyHandler(web.RequestHandler):
    @gen.coroutine
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
        # TODO - check status, set headers?
        response = yield httpclient.fetch(path)
        body = response.body
        if response.headers['content-type'].startswith('text/html'):
            body = transform_html(body)
        self.write(body)
        self.finish()


def transform_html(html: bytes) -> bytes:
    soup = BeautifulSoup(html, 'lxml')

    js_tag = soup.new_tag('script', type='text/javascript')
    injected_js = (Path(STATIC_ROOT) / 'js' / 'injected.js').read_text('utf8')
    js_tag.string = injected_js
    soup.find('body').append(js_tag)

    css_tag = soup.new_tag('style')
    injected_css = (
        Path(STATIC_ROOT) / 'css' / 'injected.css').read_text('utf8')
    css_tag.string = injected_css
    # TODO - create "head" if none exists
    soup.find('head').append(css_tag)

    return soup.encode()


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
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    app = tornado.web.Application(
        [
            web.URLSpec(r'/', MainHandler, name='main'),
            web.URLSpec(r'/(.*)', ProxyHandler, name='proxy'),
        ],
        debug=args.debug,
        static_prefix='/static/',
        static_path=STATIC_ROOT,
    )
    app.listen(args.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
