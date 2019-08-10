try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from Cython.Build import cythonize

# To compile, type: "python manhattan_sphere_setup.py build_ext --inplace" in terminal
setup(
    ext_modules = cythonize("manhattan_sphere.pyx")
)