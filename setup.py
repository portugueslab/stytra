from distutils.core import setup
from setuptools import find_packages


setup(
    name="stytra",
    version="0.1",
    author="Vilim Stih, Luigi Petrucco @portugueslab",
    author_email="vilim@neuro.mpg.de",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "pyqtgraph>=0.10.0",
        "numpy",
        "numba",
        "matplotlib",
        "pandas",
        "qdarkstyle",
        "qimage2ndarray",
        "deepdish",
        "param",
        "pims",
        "GitPython",
        "pymongo",
        "colorspacious",
        "arrayqueues",
        "pillow",
        "scikit-image",
        "filterpy",
        "multiprocessing-logging",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    keywords="tracking processing",
    description="A modular package to control stimulation and track behaviour in zebrafish experiments.",
    project_urls={
        "Source": "https://github.com/portugueslab/stytra",
        "Tracker": "https://github.com/portugueslab/stytra/issues",
    },
)
