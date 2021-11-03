.PHONY: tests

tests:
	pip install -r requirements_dev.txt
	pip install -e .
	pytest -s test_eye_tracking.py 