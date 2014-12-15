SERVER_URL = http://localhost:5000
READINGLIST_SETTINGS = $(shell pwd)/readinglist.ini

serve:
	python run.py

test:
	EVE_SETTINGS=$(READINGLIST_SETTINGS) nosetests -s

bench:
	loads-runner --config=./loadtests/bench.ini --server-url=$(SERVER_URL) loadtests.TestPOC.test_all
