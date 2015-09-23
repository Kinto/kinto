SERVER_CONFIG = config/kinto.ini

VIRTUALENV = virtualenv
SPHINX_BUILDDIR = docs/_build
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp

.IGNORE: clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

install-postgres: $(INSTALL_STAMP) $(DEV_STAMP)
	$(VENV)/bin/pip install "cliquet[postgresql]"

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -Ur dev-requirements.txt
	touch $(DEV_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	virtualenv $(VENV)

serve: install-dev migrate
	$(VENV)/bin/pserve $(SERVER_CONFIG) --reload

migrate: install
	$(VENV)/bin/cliquet --ini $(SERVER_CONFIG) migrate

tests-once: install-dev
	$(VENV)/bin/py.test --cov-report term-missing --cov-fail-under 100 --cov kinto

tests:
	tox

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -fr {} \;

loadtest-check-tutorial: install-postgres
	$(VENV)/bin/cliquet --ini loadtests/server.ini migrate > kinto.log &&\
	$(VENV)/bin/pserve loadtests/server.ini > kinto.log & PID=$$! && \
	  rm kinto.log || cat kinto.log; \
	  sleep 1 && cd loadtests && \
	  make tutorial SERVER_URL=http://127.0.0.1:8888; \
	  EXIT_CODE=$$?; kill $$PID; exit $$EXIT_CODE

loadtest-check-simulation: install-postgres
	$(VENV)/bin/cliquet --ini loadtests/server.ini migrate > kinto.log &&\
	$(VENV)/bin/pserve loadtests/server.ini > kinto.log & PID=$$! && \
	  rm kinto.log || cat kinto.log; \
	  sleep 1 && cd loadtests && \
	  make simulation SERVER_URL=http://127.0.0.1:8888; \
	  EXIT_CODE=$$?; kill $$PID; exit $$EXIT_CODE

docs: install-dev
	$(VENV)/bin/sphinx-build -b html -d $(SPHINX_BUILDDIR)/doctrees docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"
