SERVER_CONFIG = config/kinto.ini

VIRTUALENV = virtualenv
SPHINX_BUILDDIR = docs/_build
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

.IGNORE: clean distclean maintainer-clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

install-monitoring: $(INSTALL_STAMP)
	$(VENV)/bin/pip install "cliquet[monitoring]"

install-postgres: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install "cliquet[postgresql]"

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -Ur dev-requirements.txt
	touch $(DEV_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

build-requirements:
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue .
	$(TEMPDIR)/bin/pip freeze > requirements.txt

$(SERVER_CONFIG):
	$(VENV)/bin/kinto --ini $(SERVER_CONFIG) init

serve: install-dev $(SERVER_CONFIG) migrate
	$(VENV)/bin/kinto --ini $(SERVER_CONFIG) start

migrate: install $(SERVER_CONFIG)
	$(VENV)/bin/kinto --ini $(SERVER_CONFIG) migrate

tests-once: install-dev
	$(VENV)/bin/py.test --cov-report term-missing --cov-fail-under 100 --cov kinto

flake8: install-dev
	$(VENV)/bin/flake8 kinto

tests:
	$(VENV)/bin/tox

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr

distclean: clean
	rm -fr *.egg *.egg-info/

maintainer-clean: distclean
	rm -fr .venv/ .tox/ dist/ build/

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

docs: install-dev
	$(VENV)/bin/sphinx-build -a -n -b html -d $(SPHINX_BUILDDIR)/doctrees docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"
