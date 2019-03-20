# Created at {config_file_timestamp}
# Using Kinto version {kinto_version}
# Full options list for .ini file
# https://kinto.readthedocs.io/en/latest/configuration/settings.html


[server:main]
use = egg:waitress#main
host = {host}
port = %(http_port)s


[app:main]
use = egg:kinto

# Feature settings
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#feature-settings
#
# kinto.readonly = false
# kinto.batch_max_requests = 25
# kinto.paginate_by =
# Experimental JSON-schema on collection
# kinto.experimental_collection_schema_validation = false
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#activating-the-permissions-endpoint
# kinto.experimental_permissions_endpoint = false
#
# kinto.trailing_slash_redirect_enabled = true
# kinto.heartbeat_timeout_seconds = 10

# Plugins
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#plugins
# https://github.com/uralbash/awesome-pyramid
kinto.includes = kinto.plugins.default_bucket
                 kinto.plugins.admin
                 kinto.plugins.accounts
#                kinto.plugins.history
#                kinto.plugins.quotas

# Backends
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#storage
#
kinto.storage_backend = {storage_backend}
kinto.storage_url = {storage_url}
# kinto.storage_max_fetch_size = 10000
# kinto.storage_pool_size = 25
# kinto.storage_max_overflow = 5
# kinto.storage_pool_recycle = -1
# kinto.storage_pool_timeout = 30
# kinto.storage_max_backlog = -1

# Cache
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#cache
#
kinto.cache_backend = {cache_backend}
kinto.cache_url = {cache_url}
# kinto.cache_prefix =
# kinto.cache_max_size_bytes = 524288
# kinto.cache_pool_size = 25
# kinto.cache_max_overflow = 5
# kinto.cache_pool_recycle = -1
# kinto.cache_pool_timeout = 30
# kinto.cache_max_backlog = -1

# kinto.cache_backend = kinto.core.cache.memcached
# kinto.cache_hosts = 127.0.0.1:11211

# Permissions.
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#permissions
#
kinto.permission_backend = {permission_backend}
kinto.permission_url = {permission_url}
# kinto.permission_pool_size = 25
# kinto.permission_max_overflow = 5
# kinto.permission_pool_recycle = 1
# kinto.permission_pool_timeout = 30
# kinto.permission_max_backlog - 1
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#bypass-permissions-with-configuration
# kinto.bucket_create_principals = system.Authenticated

# Authentication
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#authentication
#
kinto.userid_hmac_secret = {secret}
multiauth.policies = account
# Any pyramid multiauth setting can be specified for custom authentication
# https://github.com/uralbash/awesome-pyramid#authentication
#
# Accounts API configuration
#
# Enable built-in plugin.
# Set `kinto.includes` to `kinto.plugins.accounts`
# Enable authenticated policy.
# Set `multiauth.policies` to `account`
multiauth.policy.account.use = kinto.plugins.accounts.AccountsPolicy
# Allow anyone to create accounts.
kinto.account_create_principals = system.Everyone
# Set user 'account:admin' as the administrator.
kinto.account_write_principals = account:admin
# Allow administrators to create buckets
kinto.bucket_create_principals = account:admin
# Enable the "account_validation" option.
# kinto.account_validation = true
# Set the sender for the validation email.
# kinto.account_validation.email_sender = "admin@example.com"
# Set the regular expression used to validate a proper email address.
# kinto.account_validation.email_regexp = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"

# Mail configuration (needed for the account validation option), see https://docs.pylonsproject.org/projects/pyramid_mailer/en/latest/#configuration
# mail.host = localhost
# mail.port = 25
# mail.username = someusername
# mail.password = somepassword

# Notifications
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#notifications
#
# Configuration example:
# kinto.event_listeners = redis
# kinto.event_listeners.redis.use = kinto_redis.listeners
# kinto.event_listeners.redis.url = redis://localhost:6379/0
# kinto.event_listeners.redis.pool_size = 5
# kinto.event_listeners.redis.listname = queue
# kinto.event_listeners.redis.actions = create
# kinto.event_listeners.redis.resources = bucket collection

# Production settings
#
# https://kinto.readthedocs.io/en/latest/configuration/production.html

# kinto.http_scheme = https
# kinto.http_host = kinto.services.mozilla.com

# Cross Origin Requests
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#cross-origin-requests-cors
#
# kinto.cors_origins = *

# Backoff indicators/end of service
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#backoff-indicators
# https://kinto.readthedocs.io/en/latest/api/1.x/backoff.html#id1
#
# kinto.backoff =
# kinto.backoff_percentage =
# kinto.retry_after_seconds = 3
# kinto.eos =
# kinto.eos_message =
# kinto.eos_url =

# Project information
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#project-information
#
# kinto.version_json_path = ./version.json
# kinto.error_info_link = https://github.com/kinto/kinto/issues/
# kinto.project_docs = https://kinto.readthedocs.io
# kinto.project_name = kinto
# kinto.project_version =
# kinto.version_prefix_redirect_enabled = true

# Application profilling
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#application-profiling
# kinto.profiler_enabled = true
# kinto.profiler_dir = /tmp/profiling

# Client cache headers
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#client-caching
#
# Every bucket objects objects and list
# kinto.bucket_cache_expires_seconds = 3600
#
# Every collection objects and list of every buckets
# kinto.collection_cache_expires_seconds = 3600
#
# Every group objects and list of every buckets
# kinto.group_cache_expires_seconds = 3600
#
# Every records objects and list of every collections
# kinto.record_cache_expires_seconds = 3600
#
# Records in a specific bucket
# kinto.blog_record_cache_expires_seconds = 3600
#
# Records in a specific collection in a specific bucket
# kinto.blog_article_record_cache_expires_seconds = 3600

# Custom ID generator for POST Requests
# https://kinto.readthedocs.io/en/latest/tutorials/custom-id-generator.html#tutorial-id-generator
#
# Default generator
# kinto.bucket_id_generator=kinto.views.NameGenerator
# Custom example
# kinto.collection_id_generator = name_generator.CollectionGenerator
# kinto.group_id_generator = name_generator.GroupGenerator
# kinto.record_id_generator = name_generator.RecordGenerator

# Enabling or disabling endpoints
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#enabling-or-disabling-endpoints
#
# This is a rather confusing setting due to naming conventions used in kinto.core
# For a more in depth explanation, refer to https://github.com/Kinto/kinto/issues/710
# kinto.endpoint_type_resource_name_method_enabled = false
# Where:
# endpoint_type: is either ``collection`` (plural, e.g. ``/buckets``) or ``record`` (single, e.g. ``/buckets/abc``);
# resource_name: is the name of the resource (e.g. ``bucket``, ``group``, ``collection``, ``record``);
# method: is the http method (in lower case) (e.g. ``get``, ``post``, ``put``, ``patch``, ``delete``).
# For example, to disable the POST on the list of buckets and DELETE on single records
# kinto.collection_bucket_post_enabled = false
# kinto.record_record_delete_enabled = false

# [uwsgi]
# wsgi-file = app.wsgi
# enable-threads = true
# socket = /var/run/uwsgi/kinto.sock
# chmod-socket = 666
# processes =  3
# master = true
# module = kinto
# harakiri = 120
# uid = kinto
# gid = kinto
# virtualenv = .venv
# lazy = true
# lazy-apps = true
# single-interpreter = true
# buffer-size = 65535
# post-buffering = 65535
# plugin = python

# Logging and Monitoring
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#logging-and-monitoring
# kinto.statsd_backend = kinto.core.statsd
# kinto.statsd_prefix = kinto
# kinto.statsd_url =

# kinto.newrelic_config =
# kinto.newrelic_env = dev

# Logging configuration

[loggers]
keys = root, kinto

[handlers]
keys = console

[formatters]
keys = color

[logger_root]
level = INFO
handlers = console

[logger_kinto]
level = DEBUG
handlers = console
qualname = kinto

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = color

[formatter_color]
class = logging_color_formatter.ColorFormatter
