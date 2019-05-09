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


cdef struct attr:
    string name
    string value

# Creates an attr.
cdef attr a(string name, string value) nogil:
    cdef attr _a
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
    Thread* threads2 = <Thread*>mem.alloc(10, sizeof(Thread))
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

cdef void _element_open(string* html, string tag, attr* attrs) nogil:
    cdef:
        int j = 0
        
    html.append(e1).append(tag)
    
    while True:
        a = attrs[j]
        if a.name == T.name:
            break
        
        html.append(e7).append(a.name).append(e6).append(a.value
            ).append(e9)
        j = j + 1
        
    html.append(e3)

cdef void _element_close(string* html, string tag) nogil:
    html.append(e4).append(tag).append(e5)

cdef string element(string* html, string tag, string inner, attr* attrs) nogil:
    _element_open(html, tag, attrs)
    html.append(inner)
    _element_close(html, tag)

cdef void div_ng(string inner, attr* attrs) nogil:
    element(&threads[openmp.omp_get_thread_num()].html, e8, inner, attrs)

cdef void div_pl(string* html, string inner, attr* attrs) nogil:
    element(html, e8, inner, attrs)


# -------------------------

# @contextmanager
# def divcm(string class_):
#     cdef int i = openmp.omp_get_thread_num()
#     cdef int index = threads[i].index
#     _element_open(<string> "div", class_)
#     yield
#     _element_close(<string> "div")


cdef int N = 1
cdef int M = 5

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

cdef string page_cython_nogil(int n, int m) nogil:
    htmlgen_start()
    cdef int j = 0
    cdef char k_str[10]

    while j < n:
        for k in range(m):
            sprintf(k_str, <char*> "%d", k)
            
            div_ng(<char*> "This is gøød", [
                a(<char*> "height", <char*> "91"),
                a(<char*> "width", <char*> k_str),
                T
            ])
            div_ng(<char*> "Classical", [
                a(<char*> "class", <char*> "it-is"),
                a(<char*> "title", <char*> "My øwesome title"),
                T
            ])
            write(<char*> "write")
        j += 1

    return htmlgen_stop()

# cdef string page_cython_parallel(int n, int m):
#     cdef:
#         int j = 0
#         int k = 0
#         int size = n * m
#         int l = 0
#         string* parts = <string*>mem.alloc(size, sizeof(string))
#         string html

#     for j in prange(n, nogil=True):
#         k = 0
#         while k < m:
#             l = j*n + k
#             parts[l] =  div_pl(<char*> "This is gøød", [
#                 a(<char*> "height", <char*> "91"),
#                 T
#             ])
#             k = k + 1

#     for part in parts[:size]:
#         html.append(part)

#     return html

cdef string my_page():
    cdef:
        int n = 5
        string* parts = <string*>mem.alloc(n, sizeof(string))
        string html
        int i

    for i in prange(n, nogil=True):
        div_pl(&parts[i], <char*> "This is gøød", [
            a(<char*> "height", <char*> "91"),
            T
        ])
        
    for part in parts[:n]:
        html.append(part)

    return html

print "#####################################"




def hmm():
    print my_page()

hmm()
    
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
    print"##############################################################"
    print name, N*M,"items took", round(took), "Milliseconds"
    print "each item took", took / float(N*M) * 1000, "u seconds"
    print
    if output is not None:
        print( output)
    
    return took

#a1 = timer("Page cython", page_cython)
d = timer("Page cython no gil", page_cython_nogil)
#c = timer("Page cython parallel", page_cython_parallel)
    
from proof_of_concept import page_pure_python
#b = timer("Page pure python", page_pure_python)

print "\n----------------------------"
#print "Speedup = ", b / float(d)

#print page()

# print my_html
# print "B"
# import lxml.html, lxml.etree
# print(lxml.etree.tostring(
#     lxml.html.fromstring(my_html), encoding='unicode', pretty_print=True))
