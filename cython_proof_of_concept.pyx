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
    string e1 = <string> '<'
    string e2 = <string> ' class="'
    string e3 = <string> '">'
    string e4 = <string> "</"
    string e5 = <string> ">"
    string e6 = <string> '<'
    string e7 = <string> '<'
    string e8 = <string> "div"


cdef void htmlgen_start() nogil:
    cdef int i = openmp.omp_get_thread_num()
    threads[i].html.append("-")
    threads[i].html.clear()
    threads[i].index = 0

cdef string htmlgen_stop() nogil:
    cdef int i = openmp.omp_get_thread_num()
    return threads[i].html

cdef void write(string html) nogil:
    cdef int i = openmp.omp_get_thread_num()
    threads[i].html.append(html)
    threads[i].index += 1

cdef void _element_open(string tag, string class_) nogil:
    write(e1)
    write(tag)
    write(e2)
    write(class_)
    write(e3)

cdef void _element_close(string tag) nogil:
    write(e4)
    write(tag)
    write(e5) 

cdef void element(string tag, string inner, string class_) nogil:
    _element_open(tag, class_)
    write(inner)
    _element_close(tag)

cdef void div(string inner, string class_) nogil:
     element(e8, inner, class_)

# @contextmanager
# def divcm(string class_):
#     cdef int i = openmp.omp_get_thread_num()
#     cdef int index = threads[i].index
#     try:
#         _element_open(<string> "div", class_)
#         yield
#         _element_close(<string> "div")
#     except DontExecuteException:
#         threads[i].html[index] = "-"



cdef int N = 1000000
cdef string s = <string> "My li is 500000"
cdef string e = <string> "Foo"

cdef string page(int n) nogil:
    cdef int j = 0
    htmlgen_start()

    
    while j < N:
    #for j in prange(n, nogil=True):
        div(s, e)
        j += 1

    
    return htmlgen_stop()

import time
def timer(name, func):
    a = time.time() * 1000
    if N < 20:
        print func(N)
    else:
        print len(func(N))
    #print func()
    b = time.time() * 1000
    took = b - a
    print name, N,"items took", round(took), "Milliseconds"
    print "each item took", took / float(N) * 1000, "u seconds"

    return took


print
print "..........................."

a = timer("page", page)
from proof_of_concept import page2
b = timer("same page from python", page2)

print "\n----------------------------"
print "Speedup = ", b / float(a)

#print page()

# print my_html
# print "B"
# import lxml.html, lxml.etree
# print(lxml.etree.tostring(
#     lxml.html.fromstring(my_html), encoding='unicode', pretty_print=True))
