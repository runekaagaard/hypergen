from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "cython_proof_of_concept",
        ["cython_proof_of_concept.pyx"],
        extra_compile_args=['-fopenmp', '-O3'],
        extra_link_args=['-fopenmp'], )
]

setup(name='wwwgen', ext_modules=cythonize(ext_modules, annotate=True))
