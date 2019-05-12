from threading import local
from contextlib import contextmanager
from collections import OrderedDict

try:
    from html import escape
except:
    from cgi import escape

data = local()


def t(s, quote=True):
    return escape(unicode(s), quote=quote)


def hypergen(func, *args, **kwargs):
    try:
        data.html = []
        data.extend = data.html.extend
        func(*args, **kwargs)
        html = u"".join(data.html)
    finally:
        data.html = []
        data.extend = None

    return html


def element(tag, *inners, **attrs):
    sep = attrs.pop("sep", u"")
    tag_open(tag, **attrs)
    write(*inners, sep=sep)
    tag_close(tag)


def tag_open(tag, **attrs):
    # For testing only, subject to change.
    sort_attrs = attrs.pop("_sort_attrs", False)
    if sort_attrs:
        attrs = OrderedDict((k, attrs[k])
                            for k in sorted(attrs, key=lambda x: x))
    e = data.extend
    e((u"<", tag))
    for k, v in attrs.iteritems():
        k = t(k).lstrip("_").replace("_", "-")
        if type(v) is bool:
            if v is True:
                e((u" ", k))
        elif k == u"style" and type(v) is dict:
            e((u" ", k, u'="', u";".join(
                t(k1) + u":" + t(v1) for k1, v1 in v.iteritems()), u'"'))
        else:
            e((u" ", k, u'="', t(v), u'"'))
    e((u'>', ))


def tag_close(tag):
    data.extend((u"</", t(tag), u">"))


def write(*inners, **kwargs):
    sep = kwargs.pop("sep", u"")
    data.extend((t(sep).join(t(inner) for inner in inners), ))


### *div* functions. ###


def div(*inners, **attrs):
    return element(u"div", *inners, **attrs)


@contextmanager
def div_cm(*inners, **attrs):
    sep = attrs.pop("sep", u"")
    tag_open(u"div", **attrs)
    write(*inners, sep=sep)
    yield
    tag_close(u"div")


def o_div(*inners, **attrs):
    sep = attrs.pop("sep", u"")
    tag_open(u"div", **attrs)
    write(*inners, sep=sep)


def c_div(*inners, **kwargs):
    sep = kwargs.pop("sep", u"")
    write(*inners, sep=sep)
    tag_close(u"div")


if __name__ == "__main__":
    # yapf: disable
    def test1():
        div("Hello, world!")
    assert hypergen(test1) == u"<div>Hello, world!</div>"

    def test2(name):
        div("Hello", name, _class="its-hyper", data_x=3.14, hidden=True,
            selected=False, style={"height": 42, "display": "none"}, sep=" ",
            _sort_attrs=True)
    assert hypergen(test2, "hypergen!") == u'<div class="its-hyper" '\
        'data-x="3.14" hidden style="display:none;height:42">'\
        'Hello hypergen!</div>'


    def test3():
        with div_cm("div", "cm", x=1, sep="_"):
            o_div(1, 2, y=1, sep="-")
            write(3, 4, sep="+")
            c_div(5, 6, sep=" ")
    print hypergen(test3)
    assert hypergen(test3) == u'<div x="1">div_cm<div y="1">1-23+45 6</div></div>'
