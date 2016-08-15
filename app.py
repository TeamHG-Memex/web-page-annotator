#!/usr/bin/env python
import os.path
import argparse

from urllib.parse import urlsplit, urljoin, unquote, urlencode
import tornado.ioloop
from tornado import web, gen
from tornado.httpclient import AsyncHTTPClient


ROOT = os.path.dirname(__file__)


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
        self.write(response.body)
        self.finish()


def is_full(url):
    return url.startswith('http://') or url.startswith('https://')


def fixed_full_url(url):
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
        static_path=os.path.join(ROOT, 'static'),
    )
    app.listen(args.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
