# Created at {config_file_timestamp}
# Using Kinto version {kinto_version}


[server:main]
use = egg:waitress#main
host = {host}
port = %(http_port)s


[app:main]
use = egg:kinto

#
# Backends.
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#storage
#
kinto.storage_backend = {storage_backend}
kinto.storage_url = {storage_url}
kinto.cache_backend = {cache_backend}
kinto.cache_url = {cache_url}
# kinto.cache_max_size_bytes = 524288
kinto.permission_backend = {permission_backend}
kinto.permission_url = {permission_url}

#
# Features.
#
# kinto.readonly = false
# kinto.bucket_create_principals = system.Authenticated
# kinto.batch_max_requests = 25

# Experimental JSON-schema on collection
# kinto.experimental_collection_schema_validation = true

#
# Plugins
#
kinto.includes = kinto.plugins.default_bucket
#                kinto.plugins.admin
#                kinto.plugins.accounts
#                kinto.plugins.history
#                kinto.plugins.quotas

#
# Auth configuration.
#
# https://kinto.readthedocs.io/en/latest/configuration/settings.html#authentication
#
kinto.userid_hmac_secret = {secret}
multiauth.policies = basicauth
# multiauth.policies = fxa basicauth

#
# Accounts API configuration.
#
# Enable built-in plugin.
# kinto.includes = kinto.plugins.accounts
# Enable authenticated policy.
# multiauth.policies = account
# multiauth.policy.account.use = kinto.plugins.accounts.authentication.AccountsAuthenticationPolicy
# Allow anyone to create accounts.
# kinto.account_create_principals = system.Everyone
# Set user 'account:admin' as the administrator.
# kinto.account_write_principals = account:admin
# kinto.account_read_principals = account:admin

#
# Firefox Accounts configuration.
#   These are working FxA credentials for localhost:8888
# kinto.includes  = kinto_fxa
# fxa-oauth.client_id = 61c3f791f740c19a
# fxa-oauth.client_secret = b13739d8a905315314b09fb7b947aaeb62b47c6a4a5efb00c378fdecacd1e95e
# fxa-oauth.oauth_uri = https://oauth-stable.dev.lcip.org/v1
# fxa-oauth.requested_scope = profile kinto
# fxa-oauth.required_scope = kinto
# fxa-oauth.relier.enabled = true
# fxa-oauth.webapp.authorized_domains = *

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
# Production settings
#
# https://kinto.readthedocs.io/en/latest/configuration/production.html
#
# kinto.statsd_backend = kinto.core.statsd
# kinto.statsd_url = udp://localhost:8125
# kinto.statsd_prefix = kinto-prod

# kinto.http_scheme = https
# kinto.http_host = kinto.services.mozilla.com

# kinto.backoff = 10
# kinto.retry_after_seconds = 30
# kinto.eos =


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


#
# Logging configuration
#

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
