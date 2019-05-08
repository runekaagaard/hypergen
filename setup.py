from distutils.core import setup
from Cython.Build import cythonize

setup(name='wwwgen', ext_modules=cythonize("proof_of_concept.pyx", annotate=True))
