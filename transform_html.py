import re
from urllib.parse import urljoin

from scrapely.htmlpage import HtmlTag, HtmlTagType, parse_html
from css_utils import process_css, wrap_url, unescape


URI_ATTRIBUTES = ("action", "background", "cite", "classid", "codebase",
                  "data", "href", "longdesc", "profile", "src", "usemap")

BLOCKED_TAGNAMES = ('script', 'noscript', 'object', 'embed')

_ALLOWED_CHARS_RE = re.compile('[^!-~]') # [!-~] = ascii printable characters


def _contains_js(url):
    return _ALLOWED_CHARS_RE.sub('', url).lower().startswith('javascript:')


def html4annotation(htmlpage, baseurl=None, proxy_resources=False):
    """Convert the given html document for the annotation UI

    This adds tags, removes scripts and optionally adds a base url
    """
    # htmlpage = add_tagids(htmlpage)
    cleaned_html = descriptify_and_proxy(
        htmlpage, baseurl, proxy=proxy_resources)
    return cleaned_html


def descriptify_and_proxy(doc, base=None, proxy=None):
    """Clean JavaScript in a html source string.
    """
    parsed = parse_html(doc)
    newdoc = []
    inserted_comment = False
    for element in parsed:
        if isinstance(element, HtmlTag):
            if element.tag in BLOCKED_TAGNAMES:
                # Assumes there are no void elements in BLOCKED_TAGNAMES
                # http://www.w3.org/TR/html5/syntax.html#void-elements
                if not inserted_comment and element.tag_type in (
                        HtmlTagType.OPEN_TAG, HtmlTagType.UNPAIRED_TAG):
                    newdoc.append('<%s>' % element.tag)
                    inserted_comment = True
                elif element.tag_type == HtmlTagType.CLOSE_TAG:
                    newdoc.append('</%s>' % element.tag)
                    inserted_comment = False
            elif element.tag == 'base':
                element.attributes = {}
                newdoc.append(serialize_tag(element))
            else:
                for key, val in element.attributes.copy().items():
                    _process_element(key, val, element, base, proxy)
                newdoc.append(serialize_tag(element))
        else:
            text = doc[element.start:element.end]
            if inserted_comment and text.strip():
                newdoc.append('<!-- Removed by portia -->')
            else:
                newdoc.append(text)

    return ''.join(newdoc)


def _process_element(key, val, element, base, proxy):
    # Empty intrinsic events
    if key.startswith('on') or key == 'http-equiv':
        element.attributes[key] = ''
    elif base and proxy and key == 'style' and val is not None:
        element.attributes[key] = process_css(val, -1, base)
    elif element.tag in ('frame', 'iframe') and key == 'src':
        element.attributes[key] = '/static/frames-not-supported.html'
    # Rewrite javascript URIs
    elif key in URI_ATTRIBUTES and val is not None:
        if _contains_js(unescape(val)):
            element.attributes[key] = '#'
        elif base and proxy and not (element.tag == 'a' and key == 'href'):
            element.attributes[key] = wrap_url(val, -1, base)
            element.attributes['_original_%s' % key] = val
        elif base:
            element.attributes[key] = urljoin(base, val)


def serialize_tag(tag):
    """
    Converts a tag into a string when a slice [tag.start:tag.end]
    over the source can't be used because tag has been modified
    """
    out = '<'
    if tag.tag_type == HtmlTagType.CLOSE_TAG:
        out += '/'
    out += tag.tag

    attributes = []
    for key, val in tag.attributes.items():
        aout = key
        if val is not None:
            aout += '=' + _quotify(val)
        attributes.append(aout)
    if attributes:
        out += ' ' + ' '.join(attributes)

    if tag.tag_type == HtmlTagType.UNPAIRED_TAG:
        out += '/'
    return out + '>'


def _quotify(mystr):
    """
    quotifies an html tag attribute value.
    Assumes then, that any ocurrence of ' or " in the
    string is escaped if original string was quoted
    with it.
    So this function does not altere the original string
    except for quotation at both ends, and is limited just
    to guess if string must be quoted with '"' or "'"
    """
    quote = '"'
    l = len(mystr)
    for i in range(l):
        if mystr[i] == "\\" and i + 1 < l and mystr[i + 1] == "'":
            quote = "'"
            break
        elif mystr[i] == "\\" and i + 1 < l and mystr[i + 1] == '"':
            quote = '"'
            break
        elif mystr[i] == "'":
            quote = '"'
            break
        elif mystr[i] == '"':
            quote = "'"
            break
    return quote + mystr + quote
