import types
from urllib.parse import urlparse

from pyramid.exceptions import ConfigurationError

from kinto.core import utils


import atexit

### INSTRUMENTATION BRANCH COVERAGE DATA STRUCTURE ###
coverage_data_of_watch_execution_time = {
    "Branch 1": 0,   ## FOR BRANCH OF name in members
    "Branch 2": 0,   ## IF BRANCH OF not name.startswith("_") and is_method
    "Branch 3": 0   ## INVISIBLE ELSE BRANCH
}


try:
    import statsd as statsd_module
except ImportError:  # pragma: no cover
    statsd_module = None


class Client:
    def __init__(self, host, port, prefix):
        self._client = statsd_module.StatsClient(host, port, prefix=prefix)

    ### SELECTED FUNCTION ###
    def watch_execution_time(self, obj, prefix="", classname=None):
        classname = classname or utils.classname(obj)
        members = dir(obj)
        for name in members:
            ## BRANCH 1 ##
            coverage_data_of_watch_execution_time["Branch 1"] += 1
            value = getattr(obj, name)
            is_method = isinstance(value, types.MethodType)
            if not name.startswith("_") and is_method:
                ## BRANCH 2 ##
                coverage_data_of_watch_execution_time["Branch 2"] += 1
                statsd_key = f"{prefix}.{classname}.{name}"
                decorated_method = self.timer(statsd_key)(value)
                setattr(obj, name, decorated_method)
            else:
                ## BRANCH 3 ##
                coverage_data_of_watch_execution_time["Branch 3"] += 1

    def timer(self, key):
        return self._client.timer(key)

    def count(self, key, count=1, unique=None):
        if unique is None:
            return self._client.incr(key, count=count)
        else:
            return self._client.set(key, unique)


def statsd_count(request, count_key):
    statsd = request.registry.statsd
    if statsd:
        statsd.count(count_key)


def load_from_config(config):
    # If this is called, it means that a ``statsd_url`` was specified in settings.
    # (see ``kinto.core.initialization``)
    # Raise a proper error if the ``statsd`` module is not installed.
    if statsd_module is None:
        error_msg = "Please install Kinto with monitoring dependencies (e.g. statsd package)"
        raise ConfigurationError(error_msg)

    settings = config.get_settings()
    uri = settings["statsd_url"]
    uri = urlparse(uri)

    if settings["project_name"] != "":
        prefix = settings["project_name"]
    else:
        prefix = settings["statsd_prefix"]

    return Client(uri.hostname, uri.port, prefix)


### FUNCTION TO PRINT COVERAGE DATA INFORMATION ###
def print_coverage_data():
    def print_coverage_report(function_name, coverage_data):
        print(f"Branch Coverage Report for function {function_name}:")
        print(f"Number of Branches: {len(coverage_data)}")
        total_executed = sum(1 for count in coverage_data.values() if count > 0)
        for branch, count in coverage_data.items():
            print(f"{branch}: executed {count} time(s)")
        coverage_percentage = (total_executed / len(coverage_data)) * 100
        print(f"Total Coverage: {coverage_percentage:.2f}% \n")

    print_coverage_report("watch_execution_time", coverage_data_of_watch_execution_time)

### PRINT COVERAGE DATA AT THE END OF THE PROGRAM ###
atexit.register(print_coverage_data)
