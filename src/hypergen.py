from threading import local
from contextlib import contextmanager
try:
    from html import escape
except:
    from cgi import escape

data = local()


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


def element(tag, inner, **attrs):
    tag_open(tag, **attrs)
    data.extend((t(inner, quote=False), ))
    tag_close(tag)


def t(s, quote=True):
    return escape(unicode(s), quote=quote)


def tag_open(tag, **attrs):
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


def write(html):
    data.extend(t(html))


@contextmanager
def div_cm(**attrs):
    tag_open(u"div", **attrs)
    yield
    tag_close(u"div")


def o_div(*attrs):
    tag_open(u"div", **attrs)


def c_div(*attrs):
    tag_close(u"div")


def test():
    with div_cm(_class="no", x=92):
        element(
            "div",
            "zup",
            h=42,
            w=19,
            style={1: 2,
                   3: 4},
            height=93.12,
            foo=True)


print hypergen(test)
