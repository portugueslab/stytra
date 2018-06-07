from distutils.core import setup
from setuptools import find_packages


setup(name='stytra',
      version='0.1',
      author='Vilim Stich, Luigi Petrucco & Andreas Kist @portugueslab',
      author_email='vilim@neuro.mpg.de',
      packages=find_packages(),
      install_requires=['pyqtgraph>=0.10.0', 'numpy', 'numba',
                        'matplotlib', 'pandas', 'qdarkstyle', 'qimage2ndarray',
                        'deepdish', 'param', 'pims', 'GitPython',
                        'pymongo', 'colorspacious' ,
                        'arrayqueues'])

