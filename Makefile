SERVER_URL = http://localhost:8000

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
	$(VENV)/bin/pserve conf/readinglist.ini --reload

tests: install-dev
	$(VENV)/bin/nosetests -s --with-coverage --cover-package=readinglist

bench: install-dev
	$(VENV)/bin/loads-runner --config=./loadtests/bench.ini --server-url=$(SERVER_URL) loadtests.TestPOC.test_all
