# Created at {config_file_timestamp}
# Using Kinto version {kinto_version}

[server:main]
use = egg:waitress#main
host = {host}
port = %(http_port)s

[app:main]
use = egg:kinto

#
# Feature Setttings
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#feature-settings
#
# kinto.readonly = false
# kinto.batch_max_requests = 25
# kinto.paginate_by = none
# kinto.<object-type>_id_generator = UUID4
# kinto.experimental_collection_schema_validation = false
# kinto.experimental_permissions_endpoint = false
# kinto.trailing_slash_redirect_enabled = true
# kinto.heartbeat_timeout_seconds = 10
#

#
# Backends
#
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
kinto.cache_backend = {cache_backend}
kinto.cache_url = {cache_url}
# kinto.cache_prefix = {cache_prefix}
# kinto.cache_max_size_bytes = 524288
# kinto.cache_pool_size = 25
# kinto.cache_max_overflow = 5
# kinto.cache_pool_recycle = -1
# kinto.cache_pool_timeout = 30
# kinto.cache_max_backlog = -1
kinto.permission_backend = {permission_backend}
kinto.permission_url = {permission_url}
# kinto.permission_pool_size = 25
# kinto.permission_max_overflow = 5 
# kinto.permission_pool_recycle = -1
# kinto.permission_pool_timeout = 30
# kinto.permission_max_backlog = -1
#
#
# Bypass Permissions
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#bypass-permissions-with-configuration
#
# <resource_name>_<permission>_principals = comma,separated,principals
# ex: kinto.bucket_create_principals = system.Authenticated
#
#
# Scheme, Host, Port
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#scheme-host-and-port
#
# kinto.http_host = none
# kinto.http_scheme = none
#

#
# Logging, Monitoring
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#logging-and-monitoring
#
# kinto.logging_renderer = kinto.core.logs.ClassicLogRenderer
# kinto.statsd_backend = kinto.core.statsd
# kinto.statsd_prefix = kinto
# kinto.statsd_url = none
[loggers]
keys = root, kinto

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console

[logger_kinto]
level = DEBUG
handlers =
qualname = kinto

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] %(message)s
#
# Logging with Heka
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#logging-with-heka
# 
# enabled with:
# kinto.logging_renderer = kinto.core.logs.MozillaHekaRenderer
#
#
# Monitoring with StatsD
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#monitoring-with-statsd
#
# enable with (disabled by default):
# kinto.statsd_url = udp://localhost:8125
#
# optional:
# kinto.statsd_prefix = kinto-prod
#
#
# Monitoring with New Relic
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#monitoring-with-new-relic
#
# kinto.newrelic_config = none
# kinto.newrelic_env = none
#
# enable with (disabled by default):
# kinto.newrelic_config = /location/of/newrelic.ini
# kinto.newrelic_env = prod

#
# Auth Configuration
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#authentication
#
kinto.userid_hmac_secret = {secret}
multiauth.policies = basicauth
# multiauth.authorization_policy = kinto.authorization.AuthorizationPolicy
#
# Firefox Accounts configuration.
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#firefox-accounts
#
# These are working FxA credentials for localhost:8888
# kinto.includes  = kinto_fxa
# fxa-oauth.client_id = 61c3f791f740c19a
# fxa-oauth.client_secret = b13739d8a905315314b09fb7b947aaeb62b47c6a4a5efb00c378fdecacd1e95e
# fxa-oauth.oauth_uri = https://oauth-stable.dev.lcip.org/v1
# fxa-oauth.requested_scope = profile kinto
# fxa-oauth.required_scope = kinto
# fxa-oauth.relier.enabled = true
# fxa-oauth.webapp.authorized_domains = *

#
# Plugins
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#plugin
kinto.includes = kinto.plugins.default_bucket

#
# Notifications
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#notifications
#
# 
# Filtering
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#filtering

#
# CORS
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#cross-origin-requests-cors
#
# kinto.cors_origins = *

#
# Backoff Indicators
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#backoff-indicators
#
# kinto.backoff = none  
# kinto.retry_after_seconds = 30
# kinto.eos = none
# kinto.eos_message = none 
# kinto.eos_url = none

#
# Enabling, Disabling Endpoints
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#enabling-or-disabling-endpoints
#

#
# Activating the Flush Endpoint
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#activating-the-flush-endpoint
#
# kinto.flush_endpoint_enabled = true

#
# Activating the Permissions Endpoint
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#activating-the-permissions-endpoint
#
# kinto.experimental_permissions_endpoint = true

#
# Client cache headers
#
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

#
# Project information
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#project-information
#
# kinto.version_json_path = ./version.json
# kinto.error_info_link = https://github.com/kinto/kinto/issues/
# kinto.project_docs = https://kinto.readthedocs.io
# kinto.project_version = {project_version}
# kinto.version_prefix_redirect_enabled = true

#
# Application Profiling
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#application-profiling
#
# kinto.profiler_enabled = true
# kinto.profiler_dir = /tmp/profiling

#
# Production settings
#
# https://kinto.readthedocs.io/en/latest/configuration/production.html
#
# kinto.statsd_url = udp://localhost:8125
# kinto.statsd_prefix = kinto-prod
#
# kinto.http_scheme = https
# kinto.http_host = kinto.services.mozilla.com
#
# kinto.backoff = 10
# kinto.retry_after_seconds = 30
# kinto.eos =
#
# Running Kinto with uWSGI
#
# http://kinto.readthedocs.io/en/latest/configuration/production.html?highlight=uwsgi#running-with-uwsgi
#
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
