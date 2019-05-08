from __future__ import unicode_literals

import threading
from contextlib import contextmanager

from pyrsistent import freeze

_local = threading.local()
_local.html = []
_local.index = {"value": 0}
_local.cache = {}


cdef htmlgen(f):
    def _():
        try:
            f()
            html = u"".join(x for x in _local.html if x)
        finally:
            _local.html = []

        return html

    return _


def write(html):
    if html:
        _local.html.append(unicode(html))
        _local.index["value"] += 1


def element(tag, inner, **attrs):
    _element_open(tag, **attrs)
    write(inner)
    _element_close(tag)


def _element_open(tag, **attrs):
    html = []

    def _attr(k, v):
        k = k.rstrip("_").replace("_", "-")
        if type(v) is bool:
            return u" {}".format(k) if v else u""
        else:
            return u' {}="{}"'.format(k, v)

    html.append(u"<{}".format(tag))
    [html.append(_attr(k, v)) for k, v in attrs.iteritems()]
    html.append(">")
    write(u"".join(html))


def _element_close(tag):
    write("</{}>".format(tag))


def div(inner, **attrs):
    element("div", inner, **attrs)


@contextmanager
def divcm(**attrs):
    try:
        index = _local.index["value"]
        _element_open("div", **attrs)
        yield
        _element_close("div")
    except DontExecuteException:
        _local.html[index] = None


def h1(inner, **attrs):
    element("h1", inner, **attrs)


class DontExecuteException(Exception):
    pass


@contextmanager
def noopcm():
    try:
        yield
    except DontExecuteException:
        pass


@contextmanager
def htmlcm(**attrs):
    try:
        index = _local.index["value"]
        _element_open("html", **attrs)
        yield
        _element_close("html")
    except DontExecuteException:
        _local.html[index] = None


@contextmanager
def bodycm(**attrs):
    try:
        index = _local.index["value"]
        _element_open("body", **attrs)
        yield
        _element_close("body")
    except DontExecuteException:
        _local.html[index] = None


@contextmanager
def ulcm(**attrs):
    try:
        index = _local.index["value"]
        _element_open("ul", **attrs)
        yield
        _element_close("ul")
    except DontExecuteException:
        _local.html[index] = None


def li(inner, **attrs):
    element("li", inner, **attrs)


class Bunch(dict):
    def __getattr__(self, k):
        return self[k]


@contextmanager
def cachecm(**kwargs):
    keys = kwargs.pop("key")
    if type(keys) not in (list, tuple):
        keys = [keys]

    hash_key = hash(
        tuple([hash(x) for x in keys] + ["SEP_A"] +
              [(k, v) for k, v in kwargs.iteritems()]))

    if hash_key in _local.cache:
        write(_local.cache[hash_key])
        raise DontExecuteException()
    else:
        index0 = _local.index["value"]
        yield Bunch(kwargs)
        index1 = _local.index["value"]
        _local.cache[hash_key] = u"".join(x for x in _local.html[index0:index1]
                                          if x)


@contextmanager
def pcm(**attrs):
    try:
        index = _local.index["value"]
        _element_open("p", **attrs)
        yield
        _element_close("p")
    except DontExecuteException:
        _local.html[index] = None


def helper_1(guys):
    for guy in guys:
        h1("Hello {}".format(guy), hidden=True)


#from htmlgen import context_managers as cm


def test(_is, js, xs):
    with divcm(class_="the-class"), cachecm(js=js, nr=1, key=test) as data:
        print "This will print.", data
        h1("My things")

        with ulcm(class_="my-ul"):
            for j in data.js:
                li("My li", value=j, type_="A")

    with divcm(class_="the-class"), cachecm(js=js, nr=1, key=test) as data:
        print "This will not print. Its cached.", data
        h1("My things")

        with ulcm(class_="my-ul"):
            for j in data.js:
                li("My li", value=j, type_="A")

    with divcm(class_="out"), divcm(class_="in"), ulcm():
        li("Im a li")

    with noopcm(), cachecm(_is=_is, key=[test, 3]) as data:
        for i in data._is:
            div("Das world {}".format(i), class_="my-class", hidden=True)

    with divcm(
            class_="yeah", data_x_woot=42), cachecm(
                xs=xs, key=[test, 4]) as data:
        [write(x) for x in data.xs]

    helper_1(["World", "Mars", "Moon"])


@htmlgen
def page():
    app_state = freeze([range(10), range(10), range(4)])
    with htmlcm():
        with bodycm(), cachecm(key=page, app_state=app_state) as data:
            test(*data.app_state)


my_html = page()
#print my_html

import lxml.html, lxml.etree
print(lxml.etree.tostring(
    lxml.html.fromstring(my_html), encoding='unicode', pretty_print=True))
