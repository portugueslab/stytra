.PHONY: tests

tests:
	pytest -s ./stytra/tests/test_kalman.py 
	pytest -s ./stytra/tests/test_gratings.py 
	pytest -s ./stytra/tests/test_z_experiments.py
	pytest -s ./stytra/tests/test_eye_tracking.py
	pytest -s ./stytra/tests/test_looming.py
	pytest -s ./stytra/tests/test_examples.py
	pytest -s ./stytra/tests/test_init_gui.py



