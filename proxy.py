from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from tornado.gen import coroutine
from tornado.httpclient import AsyncHTTPClient
from tornado.web import RequestHandler

from config import Session, STATIC_ROOT
from models import get_response, save_response, Workspace, Page
from transform_html import transformed_response_body, remove_scripts_and_proxy


class ProxyHandler(RequestHandler):
    @coroutine
    def get(self, ws_id):
        session = Session()
        ws = session.query(Workspace).get(int(ws_id))
        url = self.get_argument('url')
        referer = self.get_argument('referer', None)
        page = session.query(Page).filter_by(
            workspace=ws.id, url=referer or url).one()

        headers = self.request.headers.copy()
        for field in ['cookie', 'referer']:
            try:
                del headers[field]
            except KeyError:
                pass
        if referer:
            headers['referer'] = referer

        httpclient = AsyncHTTPClient()
        session = Session()
        response = get_response(session, page, url)
        if response is None:
            # TODO - do not save errors
            response = yield httpclient.fetch(url, raise_error=False)
            response = save_response(
                session, page, url, response, is_main=referer is None)

        proxy_url_base = self.reverse_url('proxy', ws.id)

        def proxy_url(resource_url):
            return '{}?{}'.format(proxy_url_base, urlencode({
                'url': resource_url, 'referer': page.url,
            }))

        html_transformed, body = transformed_response_body(
            response, inject_scripts_and_proxy, proxy_url)
        self.write(body)
        proxied_headers = {'content-type'}  # TODO - other?
        for k, v in response.headers.get_all():
            if k.lower() in proxied_headers:
                if html_transformed and k.lower() == 'content-type':
                    # change encoding (always utf8 now)
                    v = 'text/html; charset=UTF-8'
                self.set_header(k, v)
        self.finish()


def inject_scripts_and_proxy(soup: BeautifulSoup, base_url: str, proxy_url):
    remove_scripts_and_proxy(soup, base_url=base_url, proxy_url=proxy_url)
    body = soup.find('body')
    if not body:
        return

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
