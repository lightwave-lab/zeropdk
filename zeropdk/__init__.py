import os
import logging
from zeropdk.tech import Tech  # noqa
from zeropdk import klayout_extend  # noqa

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stdout_ch = logging.StreamHandler()
logger.addHandler(stdout_ch)


DEBUG = os.environ.get("ZEROPDK_DEBUG", "false") == "true"
if DEBUG:
    stdout_ch.setLevel(logging.DEBUG)
