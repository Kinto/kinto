class ListenerBase:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, event):
        """
        :param event: Incoming event
        """
        raise NotImplementedError()
