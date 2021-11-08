.PHONY: tests

tests:
	pip install opencv-python 
	pip install -r requirements_dev.txt
	pip install opencv-python 
	pip install pyFirmata 
	pip install av 
	pip install flammkuchen 
	pip install gitpython 
	pip install lightparam 
	pip install PIMS 
	pip install qimage2ndarray 
	pip install pyqtgraph 
	pip install colorspacious 
	pip install arrayqueues 
	pip install anytree 
	pip install qdarkstyle 
	pip install psutil 
	pip install pytest-qt
	pytest -s ./stytra/tests/test_kalman.py 
	pytest -s ./stytra/tests/test_gratings.py 
	pytest -s ./stytra/tests/test_z_experiments.py
	# pytest -s ./stytra/tests/test_eye_tracking.py
	# pytest -s ./stytra/tests/test_looming.py
	# pytest -s ./stytra/tests/test_examples.py
	# pytest -s ./stytra/tests/test_init_gui.py



