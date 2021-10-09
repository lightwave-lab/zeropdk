import os
import logging
from zeropdk.tech import Tech  # noqa
from zeropdk import klayout_extend  # noqa

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stdout_ch = logging.StreamHandler()
logger.addHandler(stdout_ch)

class ZeroPDKWarning(UserWarning):
    """Warning related to the usage of ZeroPDK. The responsibility falls on the user to fix these warnings."""

DEBUG = os.environ.get("ZEROPDK_DEBUG", "false") == "true"
if DEBUG:
    logger.setLevel(logging.DEBUG)
    stdout_ch.setLevel(logging.DEBUG)
