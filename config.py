import logging
from pathlib import Path

from sqlalchemy.orm import sessionmaker


logging.basicConfig(
    format='[%(levelname)s] %(asctime)s %(message)s', level=logging.INFO)
ROOT = Path(__file__).parent
STATIC_ROOT = ROOT / 'static'

Session = sessionmaker()
