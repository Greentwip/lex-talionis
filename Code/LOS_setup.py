try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from Cython.Build import cythonize
# https://github.com/cython/cython/wiki/InstallingOnWindows
# https://github.com/cython/cython/wiki/CythonExtensionsOnWindows
# To compile, type: "python LOS_setup.py build_ext --inplace" in terminal
setup(
    ext_modules = cythonize("LOS.pyx")
)