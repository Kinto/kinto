VENV ?= .venv
PYTHON := $(VENV)/bin/python3
SPHINX_BUILDDIR ?= docs/_build

SERVER_CONFIG = config/kinto.ini
NAME := kinto
SOURCE := $(shell git config remote.origin.url | sed -e 's|git@|https://|g' | sed -e 's|github.com:|github.com/|g')
VERSION := $(shell git describe --always --tag)
COMMIT := $(shell git log --pretty=format:'%H' -n 1)

.IGNORE: clean

.DEFAULT_GOAL := help

help:
	@echo "Please use 'make <target>' where <target> is one of the following commands.\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo "\nCheck the Makefile to know exactly what each target is doing."

.PHONY: all
all: install

install: ## install dependencies and prepare environment
	uv sync

install-monitoring: ## enable monitoring features like Prometheus and Newrelic
	uv sync --extra monitoring

install-postgres: ## install postgresql support
	uv sync --extra postgresql

install-memcached: ## install memcached support
	uv sync --extra memcached

install-redis: ## install redis support
	uv sync --extra redis

install-dev: ## install dependencies and everything needed to run tests
	uv sync --all-extras

install-docs: ## install dependencies to build the docs
	uv sync
	uv pip install -r docs/requirements.txt

pull-kinto-admin: kinto/plugins/admin/build ## pull the Kinto admin UI plugin
kinto/plugins/admin/build:
	scripts/pull-kinto-admin.sh

$(SERVER_CONFIG):
	$(VENV)/bin/kinto init --ini $(SERVER_CONFIG)

version-file: version.json
version.json:
	echo '{"name":"$(NAME)","version":"$(VERSION)","source":"$(SOURCE)","commit":"$(COMMIT)"}' > version.json

.PHONY: serve
serve: install-dev $(SERVER_CONFIG) migrate version-file  ## start the kinto server on default port
	$(VENV)/bin/kinto start --ini $(SERVER_CONFIG) --reload

.PHONY: migrate
migrate: install $(SERVER_CONFIG)
	$(VENV)/bin/kinto migrate --ini $(SERVER_CONFIG)

.PHONY: test
test: tests ## run all the tests with all the supported python interpreters (same as CI)
.PHONY: test-once
tests-once: tests
.PHONY: tests
tests: version-file install-dev
	$(VENV)/bin/py.test --cov-config pyproject.toml --cov-report term-missing --cov-fail-under 100 --cov kinto
.PHONY: tests-raw
tests-raw: version-file install-dev
	$(VENV)/bin/py.test
.PHONY: test-deps
test-deps:
	docker pull memcached
	docker pull redis
	docker pull postgres
	docker run -p 11211:11211 --name kinto-memcached -d memcached || echo "cannot start memcached, already exists?"
	docker run -p 6379:6379 --name kinto-redis -d redis || echo "cannot start redis, already exists?"
	docker run -p 5432:5432 --name kinto-postgres -e POSTGRES_PASSWORD=postgres -d postgres  || echo "cannot start postgres, already exists?"
	sleep 2
	PGPASSWORD=postgres psql -c "CREATE DATABASE testdb ENCODING 'UTF8' TEMPLATE template0;" -U postgres -h localhost

.PHONY: lint
lint: install-dev ## run the code linters
	$(VENV)/bin/ruff check kinto tests docs/conf.py
	$(VENV)/bin/ruff format --check kinto tests docs/conf.py
	$(VENV)/bin/ty check kinto tests

.PHONY: format
format: install-dev ## reformat code
	$(VENV)/bin/ruff check --fix kinto tests docs/conf.py
	$(VENV)/bin/ruff format kinto tests docs/conf.py

.PHONY: tdd
tdd: install-dev ## run pytest-watch to rerun tests automatically on changes for tdd
	$(VENV)/bin/ptw --runner $(VENV)/bin/py.test

need-kinto-running:
	@curl http://localhost:8888/v0/ 2>/dev/null 1>&2 || (echo "Run 'make runkinto' before starting tests." && exit 1)

.PHONY: runkinto
runkinto: install-dev ## run a kinto server
	$(VENV)/bin/kinto migrate --ini tests/functional.ini
	PROMETHEUS_MULTIPROC_DIR=/tmp/metrics KINTO_INI=tests/functional.ini $(VENV)/bin/granian --interface wsgi --port 8888 app:application

.PHONY: functional
functional: install-dev need-kinto-running ## run functional tests against a real kinto
	$(VENV)/bin/py.test tests/functional.py

.PHONY: browser-test
browser-test: need-kinto-running ## run browser tests against a real kinto
	$(VENV)/bin/playwright install firefox
	$(VENV)/bin/py.test tests/browser.py

clean: ## remove built files and start fresh
	rm -fr .venv .coverage .pytest_cache/ .ruff_cache/
	find . -name '__pycache__' -type d | xargs rm -fr
	rm -fr docs/_build/
	rm -fr kinto/plugins/admin/build/ kinto/plugins/admin/node_modules/
	docker rm -f kinto-memcached || echo ""
	docker rm -f kinto-postgres || echo ""
	docker rm -f kinto-redis || echo ""

docs: install-docs ## build the docs
	$(VENV)/bin/sphinx-build -a -W -n -b html -d $(SPHINX_BUILDDIR)/doctrees docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"

.PHONY: build
build: ## build the docker image
	docker build --build-arg="KINTO_VERSION=$(shell git describe --abbrev=0)" --pull -t kinto/kinto-server:latest .

.PHONY: test-description
test-description: install-dev ## test the built wheel metadata
	$(VENV)/bin/python -m build
	$(VENV)/bin/twine check dist/*.whl
