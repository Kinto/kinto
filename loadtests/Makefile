VIRTUALENV=virtualenv
VENV := $(shell echo $${VIRTUAL_ENV-.venv})
PYTHON=$(VENV)/bin/python

TEST_SUITE = simulation.SimulationLoadTest.test_simulation
CONFIG = test.ini

# Hackety-hack around OSX system python bustage.
# The need for this should go away with a future osx/xcode update.
ARCHFLAGS = -Wno-error=unused-command-line-argument-hard-error-in-future
INSTALL = ARCHFLAGS=$(ARCHFLAGS) $(VENV)/bin/pip install

.PHONY: install clean bench megabench

$(PYTHON):
	$(VIRTUALENV) $(VENV)

# Build virtualenv, to ensure we have all the dependencies.
.env.install: $(PYTHON)
	$(INSTALL) git+git://github.com/mozilla-services/loads.git  >> loadtest.log && \
	rm loadtest.log || cat loadtest.log
	touch $@

install: .env.install

# Clean all the things installed by `make install`.
clean:
	rm -rf .venv *.pyc .env.install

# Run a single test from the venv machine, for sanity-checking.
test: install
	$(VENV)/bin/loads-runner --config=$(CONFIG) --server-url=$(SERVER_URL) $(TEST_SUITE)
