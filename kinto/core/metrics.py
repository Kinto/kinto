from zope.interface import Interface


class IMetricsService(Interface):
    """
    An interface that defines the metrics service contract.
    Any class implementing this must provide all its methods.
    """

    def watch_execution_time(obj, prefix="", classname=None):
        """
        TODO: move this elsewhere since it's not specific by implementer.
        Decorate all methods of an object in order to watch their execution time.
        Metrics will be named `{prefix}.{classname}.{method}`.
        """

    def timer(key):
        """
        Watch execution time.
        """

    def count(key, count=1, unique=None):
        """
        Count occurrences. If `unique` is set, overwrites the counter value
        on each call.
        """
