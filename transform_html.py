import re
import html.entities
from urllib.parse import urlparse, urljoin, urlencode

from bs4 import BeautifulSoup, Tag


URI_ATTRIBUTES = {'action', 'background', 'cite', 'classid', 'codebase',
                  'data', 'href', 'longdesc', 'profile', 'src', 'usemap'}
BLOCKED_TAGNAMES = {'script', 'noscript', 'object', 'embed'}
_ALLOWED_CHARS_RE = re.compile('[^!-~]') # [!-~] = ascii printable characters


def descriptify_and_proxy(soup: BeautifulSoup, base_url: str, proxy_url: str):
    """ Clean JavaScript in a html source string
    and change urls to make them go via the proxy.
    """
    for element in soup.find_all():
        if isinstance(element, Tag):
            if element.name in BLOCKED_TAGNAMES:
                element.decompose()
            elif element.name == 'base':
                element.attrs = {}
            elif element.name is not None:  # not removed by .decompose()
                for key, val in list(element.attrs.items()):
                    _process_attr(key, val, element, base_url, proxy_url)


def _process_attr(
        key: str, val: str, element: Tag, base_url: str, proxy_url: str):
    # Empty intrinsic events
    if key.startswith('on') or key == 'http-equiv':
        element.attrs[key] = ''
    elif key == 'style' and val is not None:
        element.attrs[key] = process_css(val,  base_url, proxy_url)
    elif element.name in ('frame', 'iframe') and key == 'src':
        # TODO - add this file, use reverse
        element.attrs[key] = '/static/frames-not-supported.html'
    # Rewrite javascript URIs
    elif key in URI_ATTRIBUTES and val is not None:
        if _contains_js(unescape(val)):
            element.attrs[key] = '#'
        elif not (element.name == 'a' and key == 'href'):
            element.attrs[key] = wrap_url(val, base_url, proxy_url)
            element.attrs['_original_{}'.format(key)] = val
        else:
            element.attrs[key] = urljoin(base_url, val)


def _contains_js(url):
    return _ALLOWED_CHARS_RE.sub('', url).lower().startswith('javascript:')


CSS_IMPORT = re.compile(r'''@import\s*["']([^"']+)["']''')
CSS_URL = re.compile(r'''\burl\(("[^"]+"|'[^']+'|[^"')][^)]+)\)''')
BAD_CSS = re.compile(r'''(-moz-binding|expression\s*\(|javascript\s*:)''', re.I)


# https://html.spec.whatwg.org/multipage/syntax.html#character-references
# http://stackoverflow.com/questions/18689230/why-do-html-entity-names-with-dec-255-not-require-semicolon
_ENTITY_RE = re.compile('&#?\w+;', re.I)


def _replace_entity(match):
    entity = match.group(0)
    if entity[:2] == '&#':  # character reference
        if entity[:3] == '&#x':
            return chr(int(entity[3:-1], 16))
        else:
            return chr(int(entity[2:-1]))
    else:  # named entity
        try:
            return chr(html.entities.name2codepoint[entity[1:-1]])
        except KeyError:
            pass
        return entity  # leave as is


def unescape(s):
    """ Replaces all numeric html entities by its unicode equivalent.
    """
    return _ENTITY_RE.sub(_replace_entity, s)


def wrap_url(url, base_url, proxy_url):
    url = url.strip()
    referer = urlparse(base_url.strip()).netloc
    url = urljoin(base_url, url)
    parsed = urlparse(url)

    if parsed.scheme == 'data':
        return url  # TODO: process CSS inside data: urls
    if parsed.scheme not in ('', 'http', 'https', 'ftp'):
        return 'data:text/plain,invalid_scheme'

    return '{}?{}'.format(proxy_url, urlencode({
        'url': unescape(url),
        'referer': referer,
    }))


def process_css(css_source, base_uri, proxy_url):
    """
    Wraps urls in css source.

    >>> url = 'http://scrapinghub.com/style.css'
    >>> process_css('@import "{}"'.format(url), url, '/proxy') # doctest: +ELLIPSIS
    '@import "/proxy?..."'
    """
    def _absolutize_css_import(match):
        return '@import "{}"'.format(
            wrap_url(match.group(1), base_uri, proxy_url).replace('"', '%22'))

    def _absolutize_css_url(match):
        url = match.group(1).strip("\"'")
        return 'url("{}")'.format(
            wrap_url(url, base_uri, proxy_url).replace('"', '%22'))

    css_source = CSS_IMPORT.sub(_absolutize_css_import, css_source)
    css_source = CSS_URL.sub(_absolutize_css_url, css_source)
    css_source = BAD_CSS.sub('portia-blocked', css_source)
    return css_source
