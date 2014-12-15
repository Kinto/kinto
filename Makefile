SERVER_URL = http://localhost:5000

serve:
	python run.py

bench:
	loads-runner --config=./loadtests/bench.ini --server-url=$(SERVER_URL) loadtests.TestPOC.test_all
