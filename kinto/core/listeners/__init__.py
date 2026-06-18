from typing import Any


class ListenerBase:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __call__(self, event: Any) -> None:
        """
        :param event: Incoming event
        """
        raise NotImplementedError()
