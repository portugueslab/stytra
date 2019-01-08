from distutils.core import setup
from setuptools import find_packages


setup(
    name="stytra",
    version="0.7.3",
    author="Vilim Stih, Luigi Petrucco @portugueslab",
    author_email="vilim@neuro.mpg.de",
    license="GPLv3+",
    packages=find_packages(),
    install_requires=[
        "pyqtgraph>=0.10.0",
        "numpy",
        "numba",
        "pandas",
        "qdarkstyle",
        "qimage2ndarray",
        "deepdish",
        "pims",
        "GitPython",
        "colorspacious",
        "arrayqueues>=1.1.0b0",
        "pillow",
        "scikit-image",
        "imageio",
        "lightparam>=0.3.5",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    keywords="tracking behavior experiments",
    description="A modular package to control stimulation and track behavior in zebrafish experiments.",
    project_urls={
        "Source": "https://github.com/portugueslab/stytra",
        "Tracker": "https://github.com/portugueslab/stytra/issues",
    },
    include_package_data=True,
)
