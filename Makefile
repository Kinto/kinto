SERVER_CONFIG = config/cliquet.ini

VIRTUALENV = virtualenv
SPHINX_BUILDDIR = cliquet_docs/_build
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp

.IGNORE: clean distclean maintainer-clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON) setup.py
	$(VENV)/bin/pip install -Ue .
	touch $(INSTALL_STAMP)

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -r dev-requirements.txt
	touch $(DEV_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)
	$(VENV)/bin/pip install -U pip

build-requirements:
	@rm -fr /tmp/cliquet
	$(VIRTUALENV) /tmp/cliquet
	/tmp/cliquet/bin/pip install -Ue ".[monitoring,postgresql]"
	/tmp/cliquet/bin/pip freeze | tail -n +2 > requirements.txt

tests-once: install-dev
	@rm -fr .coverage
	$(VENV)/bin/nosetests -s --with-mocha-reporter --with-coverage --cover-min-percentage=100 --cover-package=cliquet

tests:
	$(VENV)/bin/tox

loadtest-check-simulation:
	$(VENV)/bin/pip install -Ue ".[monitoring,postgresql]" waitress
	$(VENV)/bin/cliquet --ini loadtests/testapp.ini migrate > loadtest.log &&\
	$(VENV)/bin/pserve loadtests/testapp.ini > loadtest.log & PID=$$! && \
	  rm loadtest.log || cat loadtest.log; \
	  sleep 1 && cd loadtests && \
	  make test SERVER_URL=http://127.0.0.1:8888; \
	  EXIT_CODE=$$?; kill $$PID; exit $$EXIT_CODE

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d | xargs rm -fr
	rm -fr docs/_build/

distclean: clean
	rm -fr *.egg *.egg-info/ dist/ build/

maintainer-clean: distclean
	rm -fr .venv/ .tox/

docs: install-dev
	$(VENV)/bin/sphinx-build -a -n -b html -d $(SPHINX_BUILDDIR)/doctrees cliquet_docs $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html/index.html"
