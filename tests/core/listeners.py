import json

from kinto.core import logger
from kinto.core.listeners import ListenerBase


class Listener(ListenerBase):
    """
    A demo listener that just log received info in the stdout.
    """
    def __call__(self, event):
        try:
            logger.info(json.dumps(event.payload))
        except TypeError:
            logger.error("Unable to dump the payload", exc_info=True)
            return


def load_from_config(config, prefix):
    return Listener()
