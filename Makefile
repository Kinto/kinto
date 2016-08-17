SERVER_CONFIG = config/kinto.ini

VIRTUALENV = virtualenv
SPHINX_BUILDDIR = docs/_build
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
DOC_STAMP = $(VENV)/.doc_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

.IGNORE: clean distclean maintainer-clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  install                     install dependencies and prepare environment"
	@echo "  install-monitoring          enable monitoring features like StatsD and Newrelic"
	@echo "  install-postgres            install postgresql support"
	@echo "  install-dev                 install dependencies and everything needed to run tests"
	@echo "  build-requirements          install all requirements and freeze them in requirements.txt"
	@echo "  serve                       start the kinto server on default port"
	@echo "  migrate                     run the kinto migrations"
	@echo "  tests-once                  only run the tests once with the default python interpreter"
	@echo "  flake8                      run the flake8 linter"
	@echo "  tests                       run all the tests with all the supported python interpreters (same as travis)"
	@echo "  clean                       remove *.pyc files and __pycache__ directory"
	@echo "  distclean                   remove *.egg-info files and *.egg, build and dist directories"
	@echo "  maintainer-clean            remove the .tox and the .venv directories"
	@echo "  loadtest-check-tutorial     load test the using tutorial"
	@echo "  loadtest-check-simulation   load test using a simulation"
	@echo "  docs                        build the docs"
	@echo "Check the Makefile to know exactly what each target is doing."

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

install-monitoring: $(INSTALL_STAMP)
	$(VENV)/bin/pip install -Ue ".[monitoring]"

install-postgres: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install -Ue ".[postgresql]"

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

build-requirements:
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue ".[monitoring,postgresql]"
	$(TEMPDIR)/bin/pip freeze > requirements.txt

$(SERVER_CONFIG):
	$(VENV)/bin/kinto --ini $(SERVER_CONFIG) init

NAME := kinto
SOURCE := $(shell git config remote.origin.url | sed -e 's|git@|https://|g' | sed -e 's|github.com:|github.com/|g')
VERSION := $(shell git describe --always --tag)
COMMIT := $(shell git log --pretty=format:'%H' -n 1)
version-file:
	echo '{"name":"$(NAME)","version":"$(VERSION)","source":"$(SOURCE)","commit":"$(COMMIT)"}' > version.json

serve: install-dev $(SERVER_CONFIG) migrate version-file
	$(VENV)/bin/kinto --ini $(SERVER_CONFIG) start --reload

migrate: install $(SERVER_CONFIG)
	$(VENV)/bin/kinto --ini $(SERVER_CONFIG) migrate

tests-once: install-dev version-file install-postgres install-monitoring
	$(VENV)/bin/py.test --cov-report term-missing --cov-fail-under 100 --cov kinto

flake8: install-dev
	$(VENV)/bin/flake8 kinto

tests: version-file
	$(VENV)/bin/tox

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr
	rm -fr docs/_build/

distclean: clean
	rm -fr *.egg *.egg-info/ dist/ build/

maintainer-clean: distclean
	rm -fr .venv/ .tox/

loadtest-check-tutorial: install-postgres
	$(VENV)/bin/kinto --ini loadtests/server.ini migrate > kinto.log &&\
	$(VENV)/bin/kinto --ini loadtests/server.ini start > kinto.log & PID=$$! && \
	  rm kinto.log || cat kinto.log; \
	  sleep 1 && cd loadtests && \
	  make tutorial SERVER_URL=http://127.0.0.1:8888; \
	  EXIT_CODE=$$?; kill $$PID; exit $$EXIT_CODE

loadtest-check-simulation: install-postgres
	$(VENV)/bin/kinto --ini loadtests/server.ini migrate > kinto.log &&\
	$(VENV)/bin/kinto --ini loadtests/server.ini start > kinto.log & PID=$$! && \
	  rm kinto.log || cat kinto.log; \
	  sleep 1 && cd loadtests && \
	  make simulation SERVER_URL=http://127.0.0.1:8888; \
	  EXIT_CODE=$$?; kill $$PID; exit $$EXIT_CODE

docs: install-docs
	$(VENV)/bin/sphinx-build -a -W -n -b html -d $(SPHINX_BUILDDIR)/doctrees docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"
