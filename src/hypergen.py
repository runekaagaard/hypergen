from threading import local
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
    data.extend((inner, ))
    tag_close(tag)


def tag_open(tag, **attrs):
    e = data.extend
    e((u"<", tag))
    for k, v in attrs.iteritems():
        k = unicode(k)
        if type(v) is bool:
            if v is True:
                e((u" ", k))
        elif k == u"style" and type(v) is dict:
            e((u" ", k, u'="', u";".join(
                unicode(k1) + u":" + unicode(v1)
                for k1, v1 in v.iteritems()), u'"'))
        else:
            v = unicode(v)
            e((u" ", k, u'="', escape(v, quote=True), u'"'))
    e((u'>', ))


def tag_close(tag):
    data.extend((u"</", unicode(tag), u">"))


def write(html):
    data.extend(escape(unicode(html), quote=False))


def test():
    element(
        "div", "zup", h=42, w=19, style={1: 2,
                                         3: 4}, height=93.12, foo=True)


print hypergen(test)
