from distutils.core import setup
from setuptools import find_packages


setup(name='stytra',
      version='0.1',
      author='Luigi Petrucco & Vilim Stich @portugueslab',
      author_email='vilim@neuro.mpg.de',
      packages=find_packages(),
      install_requires=['PyQt5>=5.5.0', 'pyqtgraph>=0.10.0', 'numpy', 'numba',
                        'matplotlib', 'pandas', 'qdarkstyle', 'qimage2ndarray',
                        'deepdish', 'param',
                        'gitpython', 'pymongo'])

