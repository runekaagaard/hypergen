import string, sys, json
from threading import local
from contextlib import contextmanager
from collections import OrderedDict
from functools import wraps

if sys.version_info.major > 2:
    from html import escape

    def items(x):
        return x.items()

    def t(s, quote=True):
        return escape(str(s), quote=quote)

    str = unicode
else:
    from cgi import escape

    def items(x):
        return x.iteritems()

    def t(s, quote=True):
        return escape(unicode(s), quote=quote)


state = local()


class Safe(unicode):
    pass


def base65_counter():
    # THX: https://stackoverflow.com/a/49710563/164449
    abc = string.letters + string.digits + "-_:"
    base = len(abc)
    i = -1
    while True:
        i += 1
        num = i
        output = abc[num % base]  # rightmost digit

        while num >= base:
            num //= base  # move to next digit to the left
            output = abc[num % base] + output  # this digit

        yield output


UPDATE = 1


def hypergen(func, *args, **kwargs):
    try:
        state.html = []
        state.extend = state.html.extend
        state.cache_client = kwargs.pop("cache_client", None)
        state.id_counter = base65_counter()
        state.id_prefix = (kwargs.pop("id_prefix") + u"."
                           if "id_prefix" in kwargs else u"")
        state.auto_id = kwargs.pop("auto_id", False)
        state.target_id = target_id = kwargs.pop("target_id", False)
        state.liveview = kwargs.pop("liveview", False)
        as_deltas = kwargs.pop("as_deltas", False)
        func(*args, **kwargs)
        html = u"".join(state.html)
    finally:
        state.html = []
        state.extend = None
        state.cache_client = None
        state.id_counter = None
        state.id_prefix = u""
        state.liveview = False
        state.target_id = None
        state.auto_id = False

    if as_deltas:
        return [[UPDATE, target_id, html]]
    else:
        return html


def flask_liveview_hypergen(func, *args, **kwargs):
    from flask import request
    return hypergen(
        func,
        *args,
        as_deltas=request.is_xhr,
        auto_id=True,
        liveview=True,
        **kwargs)


def flask_liveview_callback_route(app, path, *args, **kwargs):
    from flask import request, jsonify

    def _(f):
        @app.route(path, methods=["POST"], *args, **kwargs)
        @wraps(f)
        def __():
            with app.app_context():
                return jsonify(f(*request.get_json()))

        __.hypergen_url = path
        return __

    return _


def element_fn(tag, *texts, **attrs):
    sep = attrs.pop("sep", u"")
    tag_open(tag, **attrs)
    write(*texts, sep=sep)
    tag_close(tag)


def element_fn_void(tag, **attrs):
    attrs["void"] = True
    tag_open(tag, **attrs)


def element_fn_returning(tag, *texts, **attrs):
    e = state.extend
    html = []
    state.extend = html.extend
    element_fn(tag, *texts, **attrs)
    state.extend = e

    return Safe(u"".join(html))


THIS = "THIS_"


def get_liveview_arg(x, liveview_arg):
    if x == THIS:
        return json.dumps(liveview_arg)
    else:
        arg = getattr(x, "liveview_arg", None)
        if arg:
            return json.dumps(arg)
        else:
            return json.dumps(x)


def tag_open(tag, *texts, **attrs):
    # For testing only, subject to change.
    sort_attrs = attrs.pop("_sort_attrs", False)
    if sort_attrs:
        attrs = OrderedDict((k, attrs[k]) for k in sorted(attrs.keys()))
        if u"style" in attrs and type(attrs["style"]) is dict:
            attrs["style"] = OrderedDict(
                (k, attrs["style"][k]) for k in sorted(attrs["style"].keys()))

    void = attrs.pop("void", False)
    sep = attrs.pop("sep", u"")
    liveview_arg = attrs.pop("liveview_arg", None)
    e = state.extend
    e((u"<", tag))
    for k, v in items(attrs):
        k = t(k).rstrip("_").replace("_", "-")
        if state.liveview and k.startswith("on") and type(v) in (list, tuple):
            assert callable(v[0]), "First arg must be a callable."
            v = u"H({})".format(u",".join(
                get_liveview_arg(x, liveview_arg)
                for x in [v[0].hypergen_url] + list(v[1:])))
            e((u" ", k, u'="', t(v), u'"'))
        elif type(v) is bool:
            if v is True:
                e((u" ", k))
        elif k == u"style" and type(v) in (dict, OrderedDict):
            e((u" ", k, u'="', u";".join(
                t(k1) + u":" + t(v1) for k1, v1 in items(v)), u'"'))
        else:
            e((u" ", k, u'="', t(v), u'"'))
    if void:
        e(("/"))
    e((u'>', ))
    write(*texts, sep=sep)


def tag_close(tag, *texts, **kwargs):
    write(*texts, **kwargs)
    state.extend((u"</", t(tag), u">"))


def write(*texts, **kwargs):
    sep = kwargs.pop("sep", u"")
    state.extend((t(sep).join(
        t(x) if not isinstance(x, Safe) else x for x in texts
        if x is not None), ))


def raw(*texts, **kwargs):
    sep = kwargs.pop("sep", u"")
    state.extend((sep.join(texts), ))


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
def cached(ttl=3600, **kwargs):
    hash_value = "HPG{}".format(
        hash(tuple((k, kwargs[k]) for k in sorted(kwargs.keys()))))

    client = state.cache_client
    html = client.get(hash_value)

    if html is not None:
        state.extend((html, ))
        raise SkipException()
    else:
        a = len(state.html)
        kwargs.update({'hash': hash_value})
        yield Bunch(kwargs)
        b = len(state.html)
        client.set(hash_value, u"".join(x for x in state.html[a:b]), ttl)


class element(object):
    attr_forces_eval = tuple()

    # Decorator without ().
    def __new__(cls, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return cls()(args[0])
        else:
            return super(element, cls).__new__(cls, *args, **kwargs)

    def __init__(self, *texts, **attrs):
        # There are texts, so we are calling as a function.
        if texts or any(x in attrs for x in self.attr_forces_eval):
            element_fn(self.tag, *texts, **attrs)
        else:
            self.attrs = attrs

    # Context manager "with" invocation.
    def __enter__(self):
        tag_open(self.tag, **self.attrs)

    def __exit__(self, type, value, traceback):
        tag_close(self.tag)

    # Decorator with ().
    def __call__(self, func):
        def _(*args, **kwargs):
            tag_open(self.tag, **self.attrs)
            func(*args, **kwargs)
            tag_close(self.tag)

        return _

    # Return html instead of adding it to god list.
    @classmethod
    def r(cls, *texts, **attrs):
        return element_fn_returning(cls.tag, *texts, **attrs)


### div* functions. ###


def div_fn(*texts, **attrs):
    return element_fn(u"div", *texts, **attrs)


@contextmanager
def div_cm(*texts, **attrs):
    tag_open(u"div", *texts, **attrs)
    yield
    tag_close(u"div")


def div_o(*texts, **attrs):
    tag_open(u"div", *texts, **attrs)


def div_c(*texts, **attrs):
    tag_close(u"div", *texts, **attrs)


class div(element):
    tag = "div"


class p(element):
    tag = "p"


class h1(element):
    tag = "h1"


class ul(element):
    tag = "ul"


class li(element):
    tag = "li"


class code(element):
    tag = "code"


class pre(element):
    tag = "pre"


class table(element):
    tag = "table"


class tr(element):
    tag = "tr"


class th(element):
    tag = "th"


class td(element):
    tag = "td"


class a(element):
    tag = "a"


class label(element):
    tag = "label"


class html(element):
    tag = "html"


class head(element):
    tag = "head"


class body(element):
    tag = "body"


class script(element):
    tag = "script"
    attr_forces_eval = ("src", )


class style(element):
    tag = "style"
    attr_forces_eval = ("href", )


class link(element):
    tag = "link"
    attr_forces_eval = ("href", )


### input* functions ###
INPUT_TYPES = dict(checkbox="c", month="i", number="i", range="f", week="i")


def input_(**attrs):
    if state.auto_id and "id_" not in attrs:
        attrs["id_"] = next(state.id_counter)
    if "id_" in attrs:
        attrs["id_"] = state.id_prefix + attrs["id_"]
    if state.liveview:
        type_ = attrs.get("type_", "text")
        liveview_arg = attrs["liveview_arg"] = [
            "H_", INPUT_TYPES.get(type_, "s"), attrs["id_"]
        ]
    element_fn_void("input", **attrs)

    return Bunch({"liveview_arg": attrs["liveview_arg"]})


if __name__ == "__main__":
    # yapf: disable
    def test_basics():
        tag_open("li", 1, 2, a=3, b_=4, sep=".", style={1: 2}, x=True, y=False,
                 _sort_attrs=True)
        write(5, 6, sep=",")
        tag_close("li", 7, 8, sep="+")
    assert hypergen(test_basics) == u'<li a="3" b="4" style="1:2" x>1.25,67+8</li>'

    def test_basics2():
        div(111, div.r(222), 333)
    assert hypergen(test_basics2) == u'<div>111<div>222</div>333</div>'

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
        with skippable(), cached(ttl=5, key=test_cache, a=a, b=b) as value:
            div_fn(*(value.a+value.b), data_hash=value.hash)
            _h = value.hash
            _t = True

    assert hypergen(test_cache, (1, 2), (3, 4), cache_client=cache_client)\
        == u'<div data-hash="{}">1234</div>'.format(_h)
    assert _t is True
    assert hypergen(test_cache, (1, 2), (3, 4), cache_client=cache_client)\
        == u'<div data-hash="{}">1234</div>'.format(_h)
    assert _t is False
    assert hypergen(test_cache, (1, 2), (3, 5), cache_client=cache_client)\
        == u'<div data-hash="{}">1235</div>'.format(_h)
    assert _t is True

    def test_div1():
        div_fn("Hello, world!")
    assert hypergen(test_div1) == u"<div>Hello, world!</div>"

    def test_div2(name):
        div_fn("Hello", name, class_="its-hyper", data_x=3.14, hidden=True,
            selected=False, style={"height": 42, "display": "none"}, sep=" ",
            _sort_attrs=True)
    assert hypergen(test_div2, "hypergen!") == u'<div class="its-hyper" '\
        'data-x="3.14" hidden style="display:none;height:42">'\
        'Hello hypergen!</div>'

    def test_div3():
        with div_cm("div", "cm", x=1, sep="_"):
            div_o(1, 2, y=1, sep="-")
            div_c(5, 6, sep=" ")
    assert hypergen(test_div3) == u'<div x="1">div_cm<div y="1">1-25 6</div>'\
        '</div>'

    def test_div_4():
        div(x=1)
    assert hypergen(test_div_4) == ""

    def test_div_5():
        div(None, x=1)
    assert hypergen(test_div_5) == u'<div x="1"></div>'


    def test_unicorn_class1(x):
        div("yo", blink="true")
        with div():
            write(1, x)
    assert hypergen(test_unicorn_class1, 2) == \
        u'<div blink="true">yo</div><div>12</div>'

    @div
    def test_unicorn_class2(x):
        write(19, x)
    assert hypergen(test_unicorn_class2, 1) == '<div>191</div>'

    @div(id_=100)
    def test_unicorn_class3(x):
        write("hello", x)
    assert hypergen(test_unicorn_class3, 2) == '<div id="100">hello2</div>'

    def test_input():
        input_(value=1)
        input_(value=2, id_="custom")
        input_(value=3, type="number")
    assert hypergen(test_input, id_prefix="t9") == u'<input value="1"/><input '\
        'id="t9.custom" value="2"/><input type="number" value="3"/>'
    assert hypergen(test_input, id_prefix="e", liveview=True,
                    auto_id=True) == u'<input '\
        'id="e.a" value="1"/><input id="e.custom" value="2"/><input '\
        'id="e.b" type="number" value="3"/>'

    def test_liveview_events():
        def callback1(x):
            pass
        callback1.hypergen_url = "/hpg/cb1/"
        input_(value=91, onchange=(callback1, 9, [1], True, u"foo"))
    assert hypergen(test_liveview_events, id_prefix="I", liveview=True,
                    auto_id=True) == \
        u'<input id="I.a" onchange="H(&quot;/hpg/cb1/&quot;,9,[1],true,&quot;'\
        'foo&quot;)" value="91"/>'
