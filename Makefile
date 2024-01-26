SERVER_CONFIG = config/kinto.ini

SPHINX_BUILDDIR = docs/_build
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python3
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
DOC_STAMP = $(VENV)/.doc_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -du)

.IGNORE: clean distclean maintainer-clean
.PHONY: all install tests

OBJECTS = .venv .coverage

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  format                      reformat code"
	@echo "  install                     install dependencies and prepare environment"
	@echo "  install-monitoring          enable monitoring features like StatsD and Newrelic"
	@echo "  install-postgres            install postgresql support"
	@echo "  install-dev                 install dependencies and everything needed to run tests"
	@echo "  build-kinto-admin           build the Kinto admin UI plugin (requires npm)"
	@echo "  serve                       start the kinto server on default port"
	@echo "  migrate                     run the kinto migrations"
	@echo "  lint                        run the code linters"
	@echo "  tests                       run all the tests with all the supported python interpreters (same as CI)"
	@echo "  tdd                         run pytest-watch to rerun tests automatically on changes for tdd"
	@echo "  tests-once  	             only run the tests once with the default python interpreter"
	@echo "  functional                  run functional test against a real kinto"
	@echo "  browser-test                run browser test against a real kinto"
	@echo "  clean                       remove *.pyc files and __pycache__ directory"
	@echo "  distclean                   remove *.egg-info files and *.egg, build and dist directories"
	@echo "  maintainer-clean            remove the .venv directory"
	@echo "  docs                        build the docs"
	@echo "Check the Makefile to know exactly what each target is doing."

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) constraints.txt pyproject.toml
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue . -c constraints.txt
	touch $(INSTALL_STAMP)

$(PYTHON):
	python3 -m venv $(VENV)

install-monitoring: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install -Ue ".[monitoring]" -c constraints.txt

install-postgres: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install -Ue ".[postgresql]" -c constraints.txt

install-memcached: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install -Ue ".[memcached]" -c constraints.txt

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON) constraints.txt
	$(VENV)/bin/pip install -Ue ".[dev,test]" -c constraints.txt
	touch $(DEV_STAMP)

install-docs: $(DOC_STAMP)
$(DOC_STAMP): $(PYTHON) docs/requirements.txt
	$(VENV)/bin/pip install -r docs/requirements.txt
	touch $(DOC_STAMP)

constraints.txt: constraints.in
	pip-compile -o constraints.txt constraints.in

build-kinto-admin: need-npm
	scripts/build-kinto-admin.sh

$(SERVER_CONFIG):
	$(VENV)/bin/kinto init --ini $(SERVER_CONFIG)

NAME := kinto
SOURCE := $(shell git config remote.origin.url | sed -e 's|git@|https://|g' | sed -e 's|github.com:|github.com/|g')
VERSION := $(shell git describe --always --tag)
COMMIT := $(shell git log --pretty=format:'%H' -n 1)
version-file:
	echo '{"name":"$(NAME)","version":"$(VERSION)","source":"$(SOURCE)","commit":"$(COMMIT)"}' > version.json

serve: install-dev $(SERVER_CONFIG) migrate version-file
	$(VENV)/bin/kinto start --ini $(SERVER_CONFIG) --reload

migrate: install $(SERVER_CONFIG)
	$(VENV)/bin/kinto migrate --ini $(SERVER_CONFIG)

test: tests
tests-once: tests
tests: install-postgres install-monitoring install-memcached version-file install-dev
	$(VENV)/bin/py.test --cov-config pyproject.toml --cov-report term-missing --cov-fail-under 100 --cov kinto

tests-raw: version-file install-dev
	$(VENV)/bin/py.test

lint: install-dev
	$(VENV)/bin/ruff check kinto tests docs/conf.py
	$(VENV)/bin/ruff format --check kinto tests docs/conf.py

format: install-dev
	$(VENV)/bin/ruff check --fix kinto tests docs/conf.py
	$(VENV)/bin/ruff format kinto tests docs/conf.py

tdd: install-dev
	$(VENV)/bin/ptw --runner $(VENV)/bin/py.test

need-npm:
	@npm --version 2>/dev/null 1>&2 || (echo "The 'npm' command is required to build the Kinto Admin UI." && exit 1)

need-kinto-running:
	@curl http://localhost:8888/v0/ 2>/dev/null 1>&2 || (echo "Run 'make runkinto' before starting tests." && exit 1)

runkinto: install-dev
	$(VENV)/bin/kinto migrate --ini tests/functional.ini
	$(VENV)/bin/kinto start --ini tests/functional.ini

functional: install-dev need-kinto-running
	$(VENV)/bin/py.test tests/functional.py

browser-test: need-kinto-running
	$(VENV)/bin/py.test tests/browser.py

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr
	rm -fr docs/_build/

distclean: clean
	rm -fr *.egg *.egg-info/ dist/ build/

maintainer-clean: distclean
	rm -fr .venv/ kinto/plugins/admin/build/ kinto/plugins/admin/node_modules/

docs: install-docs
	$(VENV)/bin/sphinx-build -a -W -n -b html -d $(SPHINX_BUILDDIR)/doctrees docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"

.PHONY: build
build:
	docker build --build-arg="KINTO_VERSION=$(shell git describe --abbrev=0)" --pull -t kinto/kinto-server:latest .

test-description: install-dev
	$(VENV)/bin/python -m build
	$(VENV)/bin/twine check dist/*.whl
