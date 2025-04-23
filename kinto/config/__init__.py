import codecs
import logging
import os
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from time import strftime

from kinto import __version__
from kinto.core import utils as core_utils


logger = logging.getLogger(__name__)

HERE = os.path.dirname(__file__)


def render_template(template, destination, **kwargs):
    template = os.path.join(HERE, template)
    folder = os.path.dirname(destination)

    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    logger.info(f"Created config {os.path.abspath(destination)}")

    with codecs.open(template, "r", encoding="utf-8") as f:
        raw_template = f.read()
        rendered = raw_template.format_map(kwargs)
        with codecs.open(destination, "w+", encoding="utf-8") as output:
            output.write(rendered)


postgresql_url = "postgresql://postgres:postgres@localhost/postgres"

backend_to_values = {
    "postgresql": {
        "storage_backend": "kinto.core.storage.postgresql",
        "storage_url": postgresql_url,
        "permission_backend": "kinto.core.permission.postgresql",
        "permission_url": postgresql_url,
    },
    "memory": {
        "storage_backend": "kinto.core.storage.memory",
        "storage_url": "",
        "permission_backend": "kinto.core.permission.memory",
        "permission_url": "",
    },
}

cache_backend_to_values = {
    "postgresql": {"cache_backend": "kinto.core.cache.postgresql", "cache_url": postgresql_url},
    "memcached": {
        "cache_backend": "kinto.core.cache.memcached",
        "cache_url": "127.0.0.1:11211 127.0.0.2:11211",
    },
    "memory": {"cache_backend": "kinto.core.cache.memory", "cache_url": ""},
}


def init(config_file, backend, cache_backend, host="127.0.0.1"):
    values = {}

    values["host"] = host
    values["secret"] = core_utils.random_bytes_hex(32)
    values["bucket_id_salt"] = core_utils.random_bytes_hex(32)

    values["kinto_version"] = __version__
    values["config_file_timestamp"] = str(strftime("%a, %d %b %Y %H:%M:%S %z"))

    values.update(backend_to_values[backend])
    values.update(cache_backend_to_values[cache_backend])

    render_template("kinto.tpl", config_file, **values)


@lru_cache(maxsize=1)
def config_attributes():
    """
    Returns a hash of the config `.ini` file content.
    The path is only known from `app.wsgi`, so we have to read
    the environment variable again. Since tests are not run through
    WSGI, then the variable is not set.
    """
    # WARNING: this default value should be the same as `app.wsgi`
    ini_path = os.environ.get("KINTO_INI", os.path.join(".", "config", "kinto.ini"))
    if not os.path.exists(ini_path):
        logger.error(f"Could not find config file at {ini_path}")
        return None
    return {
        "path": ini_path,
        "hash": sha256(open(ini_path, "rb").read()).hexdigest(),
        "modified": datetime.fromtimestamp(os.path.getmtime(ini_path)).isoformat(),
    }
