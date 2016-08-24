from collections import deque
from functools import partial
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
    folder_name = '{}_files'.format(page.id)

    def proxy_url(url: str, include_folder: bool=False) -> str:
        file_name = '{name}{ext}'.format(
            name=hashlib.md5(url.encode('utf8', 'ignore')).hexdigest(),
            ext=get_extension(url))
        if include_folder:
            local_url = './{}/{}'.format(folder_name, file_name)
        else:
            local_url = './{}'.format(file_name)
        mapping[url] = file_name
        return local_url

    def save_response(response: Response, arcname: str=None) -> bool:
        include_folder = arcname is not None
        if arcname is None:
            try:
                file_name = mapping[response.url]
            except KeyError:
                # Perhaps we have not yet processed response that
                # references current response.
                return False
            arcname = './{}/{}'.format(folder_name, file_name)
        proxy_url_fn = partial(proxy_url, include_folder=include_folder)
        _, body = transformed_response_body(
            response, remove_scripts_and_proxy, proxy_url_fn)
        with tempfile.NamedTemporaryFile('wb', delete=False) as f:
            f.write(body)
        try:
            archive.write(f.name, arcname=arcname)
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


def get_extension(url: str, max_ext_length: int=12) -> str:
    path = urlsplit(url).path
    if '.' in path:
        ext = ''.join(re.findall(r'\w', path.rsplit('.', 1)[1]))
    else:
        return ''
    return '.{}'.format(ext[:max_ext_length]) if ext else ''
