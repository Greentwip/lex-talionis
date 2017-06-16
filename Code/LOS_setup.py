from distutils.core import setup
from Cython.Build import cythonize
# To compile, type: "python LOS_setup.py build_ext --inplace" in terminal
setup(
    ext_modules = cythonize("LOS.pyx")
)