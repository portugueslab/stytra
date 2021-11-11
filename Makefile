.PHONY: tests

tests:
	pytest -s ./stytra/tests/test_kalman.py 
	# Xvfb :1 -screen 0 640x480x8 -nolisten tcp &
	pytest -s ./stytra/tests/test_gratings.py 
	# Xvfb :1 -screen 0 640x480x8 -nolisten tcp &
	pytest -s ./stytra/tests/test_z_experiments.py
	# pytest -s ./stytra/tests/test_eye_tracking.py
	# pytest -s ./stytra/tests/test_looming.py
	# pytest -s ./stytra/tests/test_examples.py
	# Xvfb :1 -screen 0 640x480x8 -nolisten tcp &
	pytest -s ./stytra/tests/test_init_gui.py



