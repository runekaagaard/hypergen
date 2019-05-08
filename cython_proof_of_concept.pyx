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
from libcpp.vector cimport vector
from libc.stdio cimport snprintf

from pyrsistent import freeze

cdef:
    struct Thread:
        int index
        string html
    int n_threads = multiprocessing.cpu_count()
    Pool mem = Pool()
    Thread* threads = <Thread*>mem.alloc(n_threads, sizeof(Thread))
    string e1 = '<'
    string e2 = ' class="'
    string e3 = '">'
    string e4 = "</"
    string e5 = ">"
    string e6 = '<'
    string e7 = '<'
    string e8 = "div"


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

# -------------------------

cdef string pelement(string tag, string inner, string class_) nogil:
    cdef string html
    html.clear()
    
    html.append(e1)
    html.append(tag)
    html.append(e2)
    html.append(class_)
    html.append(e3)
    
    html.append(inner)
    
    html.append(e4)
    html.append(tag)
    html.append(e5)

    return html

cdef string pdiv(string inner, string class_) nogil:
    return pelement(e8, inner, class_)

@contextmanager
def divcm(string class_):
    cdef int i = openmp.omp_get_thread_num()
    cdef int index = threads[i].index
    _element_open(<string> "div", class_)
    yield
    _element_close(<string> "div")


cdef int N = 1000
cdef int M = 1000

cdef string s = "My li is 500"
cdef string e = "Foo"

cdef string page_cython(int n, int m):
    htmlgen_start()
    cdef int j = 0

    with divcm("the-class"):
        div("My things", "Foo")
        while j < n:
            for k in range(m):
                div("My li is {}".format(j), "Foo")
            j += 1

    return htmlgen_stop()
            
cdef string page_cython_nogil(int n, int m) nogil:
    htmlgen_start()
    cdef int j = 0

    while j < n:
        for k in range(m):
            div(s, e)
        j += 1

    return htmlgen_stop()

cdef string page_cython_parallel(int n, int m):
    htmlgen_start()
    
    cdef:
        int j = 0
        int k = 0
        int size = n * m
        int l = 0
        string* parts = <string*>mem.alloc(size, sizeof(string))

    for j in prange(n, nogil=True):
        k = 0
        while k < m:
            l = j*n + k
            parts[l] = pdiv(s, e)
            k = k + 1

    for part in parts[:size]:
        write(part)
    
    return htmlgen_stop()

import time
def timer(name, func):
    a = time.time() * 1000
    output = None
    if N*M < 20:
        output = func(N, M)
    else:
        func(N, M)
    #print func()
    b = time.time() * 1000
    took = b - a
    print
    print "##############################################################"
    print name, N*M,"items took", round(took), "Milliseconds"
    print "each item took", took / float(N*M) * 1000, "u seconds"
    print
    if output is not None:
        print output
    
    return took

a = timer("Page cython", page_cython)
d = timer("Page cython no gil", page_cython_nogil)
c = timer("Page cython parallel", page_cython_parallel)
    
from proof_of_concept import page_pure_python
b = timer("Page pure python", page_pure_python)

print "\n----------------------------"
print "Speedup = ", b / float(d)

#print page()

# print my_html
# print "B"
# import lxml.html, lxml.etree
# print(lxml.etree.tostring(
#     lxml.html.fromstring(my_html), encoding='unicode', pretty_print=True))
