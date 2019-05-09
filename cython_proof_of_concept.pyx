# cython: language_level=2
# distutils: language = c++


from cymem.cymem cimport Pool
    
from contextlib import contextmanager

from cpython cimport array
from cython.parallel cimport parallel
from cython.parallel import prange
cimport openmp
from cymem.cymem cimport Pool
from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdio cimport sprintf

### Type definitions ###
ctypedef fused attr_val:
    char
    string
    float

cdef struct attr_s:
    string name
    string value

ctypedef attr_s attr

# Creates an attr.
cdef attr a(string name, attr_val value) nogil:
    cdef attr _a
    #cdef char* value_c = value
    
    _a.name = <string> name
    _a.value = <string> value

    return _a

# Attribute list terminator.
cdef attr T = a(<char*> "__the_end__", <char*> "__is_reached__")


### Cdefs ###
cdef:
    struct Thread:
        string html
    int n_threads = openmp.omp_get_max_threads()
    Pool mem = Pool()
    Thread* threads = <Thread*>mem.alloc(n_threads, sizeof(Thread))
    char* e1 = '<'
    char* e2 = ' class="'
    char* e3 = '>'
    char* e4 = "</"
    char* e5 = ">"
    char* e6 = '="'
    char* e7 = ' '
    char* e8 = "div"
    char* e9 = '"'


cdef void htmlgen_start() nogil:
    cdef int i = openmp.omp_get_thread_num()
    threads[i].html.append("-")
    threads[i].html.clear()

cdef string htmlgen_stop() nogil:
    cdef int i = openmp.omp_get_thread_num()
    return threads[i].html

cdef void write(string html) nogil:
    cdef int i = openmp.omp_get_thread_num()
    threads[i].html.append(html)

cdef void _element_open(string tag, attr* attrs) nogil:
    cdef:
        int i = openmp.omp_get_thread_num()
        int j = 0
        
    threads[i].html.append(e1).append(tag)
    
    while True:
        a = attrs[j]
        if a.name == T.name:
            break
        
        threads[i].html.append(e7).append(a.name).append(e6).append(a.value
            ).append(e9)
        j = j + 1
        
    threads[i].html.append(e3)

cdef void _element_close(string tag) nogil:
    threads[openmp.omp_get_thread_num()].html.append(e4).append(tag).append(e5)

cdef void element(string tag, string inner, attr* attrs) nogil:
    _element_open(tag, attrs)
    threads[openmp.omp_get_thread_num()].html.append(inner)
    _element_close(tag)

cdef void div(string inner, attr* attrs) nogil:
    element(e8, inner, attrs)

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

# @contextmanager
# def divcm(string class_):
#     cdef int i = openmp.omp_get_thread_num()
#     cdef int index = threads[i].index
#     _element_open(<string> "div", class_)
#     yield
#     _element_close(<string> "div")


cdef int N = 1
cdef int M = 5

cdef char* s = "My li is ø 500"
cdef char* e = "Foøo"

# cdef string page_cython(int n, int m):
#     htmlgen_start()
#     cdef int j = 0

#     with divcm("the-class"):
#         div("My things", "Foo")
#         while j < n:
#             for k in range(m):
#                 div("My li is {}".format(j), "Foo")
#             j += 1

#     return htmlgen_stop()

cdef void wat(string x) nogil:
    cdef string y = <string> x

cdef string page_cython_nogil(int n, int m) nogil:
    #with gil:
    #    cdef ctuple attrs = (<string> "class", <string> "my-class") 
    htmlgen_start()
    cdef int j = 0
    cdef char k_str[10]

    while j < n:
        for k in range(m):
            sprintf(k_str, <char*> "%d", k)
            
            div(<char*> "This is gøød", [
                a(<char*> "height", <char*> "91"),
                a(<char*> "width", <char*> k_str),
                T
            ])
            div(<char*> "Classical", [
                a(<char*> "class", <char*> "it-is"),
                a(<char*> "title", <char*> "My øwesome title"),
                T
            ])
        j += 1

    return htmlgen_stop()

# cdef string wut(string, (int, int) attrs) nogil:
#     cdef char* x = "ok"
#     wat(<char*> "WUUUTæ")
#     wat(e)
#     #print html, attrs
#     #cdef string html_s = <string> html
#     pass

# cdef string page_cython_parallel(int n, int m):
#     htmlgen_start()
    
#     cdef:
#         int j = 0
#         int k = 0
#         int size = n * m
#         int l = 0
#         string* parts = <string*>mem.alloc(size, sizeof(string))

#     for j in prange(n, nogil=True):
#         k = 0
#         while k < m:
#             l = j*n + k
#             parts[l] = pdiv(s, e)
#             k = k + 1

#     for part in parts[:size]:
#         write(part)
    
#     return htmlgen_stop()

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
    print()
    print( "##############################################################")
    print( name, N*M,"items took", round(took), "Milliseconds")
    print( "each item took", took / float(N*M) * 1000, "u seconds")
    print()
    if output is not None:
        print( output)
    
    return took

#a1 = timer("Page cython", page_cython)
d = timer("Page cython no gil", page_cython_nogil)
#c = timer("Page cython parallel", page_cython_parallel)
    
from proof_of_concept import page_pure_python
#b = timer("Page pure python", page_pure_python)

print ("\n----------------------------")
#print "Speedup = ", b / float(d)

#print page()

# print my_html
# print "B"
# import lxml.html, lxml.etree
# print(lxml.etree.tostring(
#     lxml.html.fromstring(my_html), encoding='unicode', pretty_print=True))
