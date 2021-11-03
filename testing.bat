@echo off

@REM conda activate stytra_env

ECHO "Start Tesing"

cd .\stytra\tests

pytest -s test_eye_tracking.py   

ECHO "First test Done"

@REM pytest -s test_imaging.py 

ECHO "Second test not Done"

pytest -s test_gratings.py    

ECHO "Third test Done"

pytest -s test_examples.py  

ECHO "Fourth test Done"

pytest -s test_z_experiments.py  

ECHO "fifth test Done"

pytest -s test_looming.py  

ECHO "Sixth test Done"