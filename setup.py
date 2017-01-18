from distutils.core import setup
from setuptools import find_packages

setup(name='stytra',
      version='0.01',
      author='Andreas Kist & Vilim Stich',
      author_email='vilim@neuro.mpg.de',
      packages=find_packages(),
      install_requires=['PyQt5', 'pyqtgraph', 'numpy', 'numba',
                        'matplotlib', 'pandas', 'qdarkstyle'])