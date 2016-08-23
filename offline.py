from collections import deque
import hashlib
import logging
import os
import re
import tempfile
from urllib.parse import urlsplit
import zipfile

from models import Page, Response
from transform_html import remove_scripts_and_proxy, transformed_response_body


def save_page_for_offline(archive: zipfile.ZipFile, session, page: Page):
    mapping = {}  # url -> path

    def proxy_url(url: str) -> str:
        path = './{folder}_files/{name}{ext}'.format(
            folder=page.id,
            name=hashlib.md5(url.encode('utf8', 'ignore'))
                .hexdigest().encode('ascii'),
            ext=get_extension(url))
        mapping[url] = path
        return path

    def save_response(response: Response, path: str=None) -> bool:
        if path is None:
            try:
                path = mapping[response.url]
            except KeyError:
                # Perhaps we have not yet processed response that
                # references current response.
                return False
        _, body = transformed_response_body(
            response, remove_scripts_and_proxy, proxy_url)
        with tempfile.NamedTemporaryFile('wb', delete=False) as f:
            f.write(body)
        try:
            archive.write(f.name, arcname=path)
        finally:
            os.unlink(f.name)
        return True

    responses = list(session.query(Response).filter_by(page=page.id))
    if not responses:
        return
    main_response, = [r for r in responses if r.is_main]
    save_response(main_response, '{}.html'.format(page.id))

    to_save = deque(set(responses) - {main_response})
    n_iter = 0
    max_iter = len(to_save) * 2
    while to_save:
        r = to_save.popleft()
        if not save_response(r):
            to_save.append(r)
        n_iter += 1
        if n_iter == max_iter:
            logging.warning('Failed to save all responses for page id {}'
                            .format(page.id))
            break


def get_extension(url: str):
    path = urlsplit(url).path
    ext = re.findall(r'\w', path.rsplit('.', 1)[1])[:10] if '.' in path else None
    return '.{}'.format(ext) if ext else ''
