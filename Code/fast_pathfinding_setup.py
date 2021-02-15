try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from Cython.Build import cythonize
# To compile, type: "python fast_pathfinding_setup.py build_ext --inplace" in terminal
setup(
    ext_modules = cythonize("fast_pathfinding.pyx")
)