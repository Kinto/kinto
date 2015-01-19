SERVER_URL = http://localhost:8000
SERVER_CONFIG = conf/readinglist.ini

VIRTUALENV=virtualenv
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON=$(VENV)/bin/python
DEV_STAMP=$(VENV)/.dev_env_installed.stamp
INSTALL_STAMP=$(VENV)/.install.stamp

.IGNORE: clean
.PHONY: all install virtualenv tests

OBJECTS = .venv .coverage

all: install
install: $(INSTALL_STAMP)
$(INSTALL_STAMP): $(PYTHON)
	$(PYTHON) setup.py develop
	touch $(INSTALL_STAMP)

install-dev: $(INSTALL_STAMP) $(DEV_STAMP)
$(DEV_STAMP): $(PYTHON)
	$(VENV)/bin/pip install -r dev-requirements.txt
	touch $(DEV_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	virtualenv $(VENV)

serve: install-dev
	$(VENV)/bin/pserve $(SERVER_CONFIG) --reload

tests-once: install-dev
	$(VENV)/bin/nosetests -s --with-coverage --cover-package=readinglist

tests:
	tox

bench: install-dev
	$(VENV)/bin/loads-runner --config=./loadtests/bench.ini --server-url=$(SERVER_URL) loadtests.TestBasic.test_all

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -fr {} \;
