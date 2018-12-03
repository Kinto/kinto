SERVER_CONFIG = config/kinto.ini

VIRTUALENV = virtualenv --python=python3
SPHINX_BUILDDIR = docs/_build
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python3
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
DOC_STAMP = $(VENV)/.doc_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -du)

.IGNORE: clean distclean maintainer-clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  black	                     reformat code"
	@echo "  install                     install dependencies and prepare environment"
	@echo "  install-monitoring          enable monitoring features like StatsD and Newrelic"
	@echo "  install-postgres            install postgresql support"
	@echo "  install-dev                 install dependencies and everything needed to run tests"
	@echo "  build-kinto-admin           build the Kinto admin UI plugin (requires npm)"
	@echo "  serve                       start the kinto server on default port"
	@echo "  migrate                     run the kinto migrations"
	@echo "  flake8                      run the flake8 linter"
	@echo "  tests                       run all the tests with all the supported python interpreters (same as travis)"
	@echo "  tdd                         run pytest-watch to rerun tests automatically on changes for tdd"
	@echo "  tests-once  	             only run the tests once with the default python interpreter"
	@echo "  functional                  run functional test against a real kinto"
	@echo "  clean                       remove *.pyc files and __pycache__ directory"
	@echo "  distclean                   remove *.egg-info files and *.egg, build and dist directories"
	@echo "  maintainer-clean            remove the .tox and the .venv directories"
	@echo "  docs                        build the docs"
	@echo "Check the Makefile to know exactly what each target is doing."

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py requirements.txt
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue . -c requirements.txt
	touch $(INSTALL_STAMP)

install-monitoring: $(INSTALL_STAMP)
	$(VENV)/bin/pip install -Ue ".[monitoring]" -c requirements.txt

install-postgres: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install -Ue ".[postgresql]" -c requirements.txt

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -Ur dev-requirements.txt
	touch $(DEV_STAMP)

install-docs: $(DOC_STAMP)
$(DOC_STAMP): $(PYTHON) docs/requirements.txt
	$(VENV)/bin/pip install -Ur docs/requirements.txt
	touch $(DOC_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

build-kinto-admin: need-npm
	cd kinto/plugins/admin/; npm install && export REACT_APP_VERSION="$$(npm list | egrep kinto-admin | cut -d @ -f 2)" && npm run build

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

tests-once: install-dev version-file install-postgres install-monitoring
	$(VENV)/bin/py.test --cov-report term-missing --cov-fail-under 100 --cov kinto

flake8: install-dev
	$(VENV)/bin/flake8 kinto tests

black: install-dev
	$(VENV)/bin/black --exclude "/node_modules/" kinto tests

tests: version-file
	$(VENV)/bin/tox

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

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr
	rm -fr docs/_build/

distclean: clean
	rm -fr *.egg *.egg-info/ dist/ build/

maintainer-clean: distclean
	rm -fr .venv/ .tox/ kinto/plugins/admin/build/ kinto/plugins/admin/node_modules/

docs: install-docs
	$(VENV)/bin/sphinx-build -a -W -n -b html -d $(SPHINX_BUILDDIR)/doctrees docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"

build:
	docker build --pull -t kinto/kinto-server:latest .
