from threading import local
from contextlib import contextmanager
from collections import OrderedDict
import sys

if sys.version_info.major > 2:
    from html import escape

    def items(x):
        return x.items()

    def t(s, quote=True):
        return escape(str(s), quote=quote)
else:
    from cgi import escape

    def items(x):
        return x.iteritems()

    def t(s, quote=True):
        return escape(unicode(s), quote=quote)


state = local()


def hypergen(func, *args, **kwargs):
    try:
        state.html = []
        state.extend = state.html.extend
        state.cache_client = kwargs.pop("cache_client", None)
        state.hash_value = None
        func(*args, **kwargs)
        html = u"".join(state.html)
    finally:
        state.html = []
        state.extend = None
        state.cache_client = None

    return html


def element(tag, *inners, **attrs):
    sep = attrs.pop("sep", u"")
    tag_open(tag, **attrs)
    write(*inners, sep=sep)
    tag_close(tag)


def tag_open(tag, *inners, **attrs):
    # For testing only, subject to change.
    sort_attrs = attrs.pop("_sort_attrs", False)
    if sort_attrs:
        attrs = OrderedDict((k, attrs[k]) for k in sorted(attrs.keys()))
        if u"style" in attrs and type(attrs["style"]) is dict:
            attrs["style"] = OrderedDict(
                (k, attrs["style"][k]) for k in sorted(attrs["style"].keys()))

    sep = attrs.pop("sep", u"")
    e = state.extend
    e((u"<", tag))
    for k, v in items(attrs):
        k = t(k).lstrip("_").replace("_", "-")
        if type(v) is bool:
            if v is True:
                e((u" ", k))
        elif k == u"style" and type(v) in (dict, OrderedDict):
            e((u" ", k, u'="', u";".join(
                t(k1) + u":" + t(v1) for k1, v1 in items(v)), u'"'))
        else:
            e((u" ", k, u'="', t(v), u'"'))
    e((u'>', ))
    write(*inners, sep=sep)


def tag_close(tag, *inners, **kwargs):
    write(*inners, **kwargs)
    state.extend((u"</", t(tag), u">"))


def write(*inners, **kwargs):
    sep = kwargs.pop("sep", u"")
    state.extend((t(sep).join(t(inner) for inner in inners), ))


class Bunch(dict):
    def __getattr__(self, k):
        return self[k]


class SkipException(Exception):
    pass


@contextmanager
def skippable():
    try:
        yield
    except SkipException:
        pass


@contextmanager
def hashing(**kwargs):
    with skippable():
        try:
            state.hash_value = "HPG{}".format(
                hash(tuple((k, kwargs[k]) for k in sorted(kwargs.keys()))))
            kwargs.update({'hash': state.hash_value})
            yield Bunch(kwargs)
        finally:
            state.hash_value = None


@contextmanager
def caching(ttl=3600):
    client = state.cache_client
    assert state.hash_value is not None, "Missing caching context manager."
    html = client.get(state.hash_value)

    if html is not None:
        state.extend((html, ))
        raise SkipException()
    else:
        a = len(state.html)
        yield
        b = len(state.html)
        client.set(state.hash_value, u"".join(x for x in state.html[a:b]), ttl)


### *div* functions. ###


def div(*inners, **attrs):
    return element(u"div", *inners, **attrs)


@contextmanager
def div_cm(*inners, **attrs):
    tag_open(u"div", *inners, **attrs)
    yield
    tag_close(u"div")


def o_div(*inners, **attrs):
    tag_open(u"div", *inners, **attrs)


def c_div(*inners, **kwargs):
    tag_close(u"div", *inners, **kwargs)


if __name__ == "__main__":
    # yapf: disable
    def test_basics():
        tag_open("li", 1, 2, a=3, _b=4, sep=".", style={1: 2}, x=True, y=False,
                 _sort_attrs=True)
        write(5, 6, sep=",")
        tag_close("li", 7, 8, sep="+")
    assert hypergen(test_basics) == u'<li b="4" a="3" style="1:2" x>1.25,67+8</li>'

    class Cache(object):
        def __init__(self):
            self.cache = {}

        def set(self, k, v, ttl):
            self.cache[k] = v

        def get(self, k):
            return self.cache.get(k, None)
    cache_client = Cache()

    _h = None
    _t = False
    def test_cache(a, b):
        global _h, _t
        _t = False
        with hashing(key=test_cache, a=a, b=b) as hashed, caching(ttl=5):
            div(*(hashed.a+hashed.b), data_hash=hashed.hash)
            _h = hashed.hash
            _t = True
            assert state.hash_value is not None

    assert hypergen(test_cache, (1, 2), (3, 4), cache_client=cache_client)\
        == u'<div data-hash="{}">1234</div>'.format(_h)
    assert _t is True
    assert hypergen(test_cache, (1, 2), (3, 4), cache_client=cache_client)\
        == u'<div data-hash="{}">1234</div>'.format(_h)
    assert _t is False
    assert hypergen(test_cache, (1, 2), (3, 5), cache_client=cache_client)\
        == u'<div data-hash="{}">1235</div>'.format(_h)
    assert _t is True
    assert state.hash_value is None

    def test_div1():
        div("Hello, world!")
    assert hypergen(test_div1) == u"<div>Hello, world!</div>"

    def test_div2(name):
        div("Hello", name, _class="its-hyper", data_x=3.14, hidden=True,
            selected=False, style={"height": 42, "display": "none"}, sep=" ",
            _sort_attrs=True)
    assert hypergen(test_div2, "hypergen!") == u'<div class="its-hyper" '\
        'data-x="3.14" hidden style="display:none;height:42">'\
        'Hello hypergen!</div>'

    def test_div3():
        with div_cm("div", "cm", x=1, sep="_"):
            o_div(1, 2, y=1, sep="-")
            c_div(5, 6, sep=" ")
    assert hypergen(test_div3) == u'<div x="1">div_cm<div y="1">1-25 6</div>'\
        '</div>'
