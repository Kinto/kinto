import json
import logging

from kinto.core.listeners import ListenerBase


logger = logging.getLogger(__name__)


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
