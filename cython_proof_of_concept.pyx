# cython: language_level=2
# distutils: language = c++


from cymem.cymem cimport Pool
from random import random
    
import threading
from contextlib import contextmanager

from cpython cimport array
from cython.parallel cimport parallel
from cython.parallel import prange
cimport openmp
from cymem.cymem cimport Pool
import multiprocessing
from libcpp.string cimport string

from pyrsistent import freeze

cdef:
    struct Thread:
        int index
        string html
    int n_threads = multiprocessing.cpu_count()
    Pool mem = Pool()
    Thread* threads = <Thread*>mem.alloc(n_threads, sizeof(Thread))

    
class Bunch(dict):
    def __getattr__(self, k):
        return self[k]


cdef void htmlgen_start():
    cdef i = openmp.omp_get_thread_num()
    threads[i].html.append("-")
    threads[i].html.clear()
    threads[i].index = 0

cdef string htmlgen_stop():
    cdef i = openmp.omp_get_thread_num()
    return threads[i].html

cdef void write(string html):
    cdef i = openmp.omp_get_thread_num()
    threads[i].html.append(html)
    threads[i].index += 1

cdef void _element_open(string tag, string class_):
    write(<string> '<')
    write(tag)
    write(<string> ' class="')
    write(class_)
    write(<string> '">')

cdef void _element_close(string tag):
    write(<string> "</")
    write(tag)
    write(<string> ">") 

cdef void element(string tag, string inner, string class_):
    _element_open(tag, class_)
    write(<string> inner)
    _element_close(tag)

cdef void div(str inner, str class_):
     element(<string> "div", <string> inner, <string> class_)

cdef class DontExecuteException(Exception):
    pass

@contextmanager
def divcm(string class_):
    cdef int i = openmp.omp_get_thread_num()
    cdef int index = threads[i].index
    try:
        _element_open(<string> "div", class_)
        yield
        _element_close(<string> "div")
    except DontExecuteException:
        threads[i].html[index] = "-"

cdef int N = 1000000

cdef string page():
    cdef int j = 0
    htmlgen_start()
    
    with divcm("the-class"):
         div("My things", class_="Foo")
         while j < N:
            div("My li is {}".format(j), class_="Foo")
            j += 1

    
    return htmlgen_stop()

import time
def timer(name, func):
    a = time.time() * 1000
    print len(func())
    b = time.time() * 1000
    took = b - a
    print name, N,"items took", round(took), "Milliseconds"
    print "each item took", took / float(N) * 1000, "u seconds"

    return took

a = timer("page", page)

print
from proof_of_concept import page2
b = timer("same page from python", page2)

print "--------------"
print "Speedup = ", b / float(a)


# print my_html
# print "B"
# import lxml.html, lxml.etree
# print(lxml.etree.tostring(
#     lxml.html.fromstring(my_html), encoding='unicode', pretty_print=True))
