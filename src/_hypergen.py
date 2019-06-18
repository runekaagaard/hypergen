# coding=utf-8
from __future__ import (absolute_import, division, unicode_literals)

import string, sys, json
from threading import local
from contextlib import contextmanager
from collections import OrderedDict
from functools import wraps
from copy import copy
from types import GeneratorType

### Python 2+3 compatibility ###

if sys.version_info.major > 2:
    from html import escape
    letters = string.ascii_letters

    def items(x):
        return x.items()

else:
    from cgi import escape
    letters = string.letters
    str = unicode

    def items(x):
        return x.iteritems()


### Globals ###

state = local()
UPDATE = 1

### Control ###


def hypergen(func, *args, **kwargs):
    kwargs = copy(kwargs)
    auto_id = kwargs.pop("auto_id", False)
    try:
        state.html = []
        state.cache_client = kwargs.pop("cache_client", None)
        state.id_counter = base65_counter() if auto_id else None
        state.id_prefix = (kwargs.pop("id_prefix") + "."
                           if "id_prefix" in kwargs else "")
        state.auto_id = auto_id
        state.target_id = target_id = kwargs.pop("target_id", False)
        state.liveview = kwargs.pop("liveview", False)
        as_deltas = kwargs.pop("as_deltas", False)
        func(*args, **kwargs)
        html = "".join(state.html)
    finally:
        state.html = []
        state.cache_client = None
        state.id_counter = None
        state.id_prefix = ""
        state.auto_id = False
        state.liveview = False
        state.target_id = None

    if as_deltas:
        return [[UPDATE, target_id, html]]
    else:
        return html


hypergen(lambda: None)


class SkipException(Exception):
    pass


@contextmanager
def skippable():
    try:
        yield
    except SkipException:
        pass


### Building HTML, internal API ###


def element_start(tag,
                  children,
                  into=None,
                  sep="",
                  void=False,
                  liveview=None,
                  when=True,
                  **attrs):
    def sort_attrs(attrs):
        # For testing only, subject to change.
        sort_attrs = attrs.pop("_sort_attrs", False)
        if sort_attrs:
            attrs = OrderedDict((k, attrs[k]) for k in sorted(attrs.keys()))
            if "style" in attrs and type(attrs["style"]) is dict:
                attrs["style"] = OrderedDict(
                    (k, attrs["style"][k])
                    for k in sorted(attrs["style"].keys()))

        return attrs

    if when is False:
        raise SkipException()
    if into is None:
        into = state.html
    attrs = sort_attrs(copy(attrs))
    e = into.extend

    e(("<", tag))
    for k, v in items(attrs):
        k = t(k).rstrip("_").replace("_", "-")
        if k == "meta":
            continue
        elif type(v) is bool:
            if v is True:
                e((" ", k))
        elif k == "style" and type(v) in (dict, OrderedDict):
            e((" ", k, '="', ";".join(
                t(k1) + ":" + t(v1) for k1, v1 in items(v)), '"'))
        else:
            e((" ", k, '="', t(v), '"'))
    if void:
        e(("/"))
    e(('>', ))

    write(*children, into=into, sep=sep)


def element_end(tag, children, **kwargs):
    write(*children, **kwargs)
    kwargs.get("into", state.html).extend(("</", t(tag), ">"))


def element(tag, children, **attrs):
    element_start(tag, children, **attrs)
    if not attrs.get("void", False):
        element_end(tag, [], **attrs)


def element_ret(tag, children, **attrs):
    into = []
    element(tag, children, into=into, **attrs)

    return Safe("".join(into))


def element_con(tag, children, **attrs):
    element = element_start(tag, children, **attrs)
    yield element
    element_end(tag, [], **attrs)


def element_dec(tag, children, **attrs):
    def _(f):
        @wraps(f)
        def __(*args, **kwargs):
            element_start(tag, children, **attrs)
            f(*args, **kwargs)
            element_end(tag, [], **attrs)

        return __

    return _


### Building HTML, public API ###


def write(*children, **kwargs):
    into = kwargs.get("into", state.html)
    items = []
    for x in children:
        if type(x) in (list, tuple, GeneratorType):
            items.extend(t(y) for y in list(x))
        elif x is None:
            continue
        else:
            items.append(t(x))
    into.extend(t(kwargs.get("sep", "")).join(x for x in items))


def raw(*children, **kwargs):
    kwargs.get("into", state.html).extend((kwargs.get("sep",
                                                      "").join(children), ))


### Flask helpers ###


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

        __.hypergen_callback_url = path
        return __

    return _


### Misc ###


def t(s, quote=True):
    return str(s) if type(s) in (Safe, Node) else escape(str(s), quote=quote)


class Safe(str):
    pass


class Bunch(dict):
    def __getattr__(self, k):
        return self[k]


class Node(Bunch):
    def __init__(self, html, meta=None):
        self.html = html
        self.meta = meta if meta is not None else {}

    def __str__(self):
        return self.html

    def __unicode__(self):
        return self.html


def base65_counter():
    # THX: https://stackoverflow.com/a/49710563/164449
    abc = letters + string.digits + "-_:"
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


### Form elements and liveview ###

THIS = "THIS_"


class Callback(object):
    def __init__(self, func, args=None, debounce=0):
        self.func = func
        self.args = args
        self.debounce = debounce

    def render_arg(self, arg, as_callback_argument):
        if arg == THIS:
            return as_callback_argument
        else:
            try:
                return arg.meta["as_callback_argument"]
            except (TypeError, KeyError, AttributeError):
                return json.dumps(arg)

    def render(self, meta):
        liveview_args = [json.dumps(self.func.hypergen_callback_url)]
        for arg in self.args:
            liveview_args.append(self.render_arg(arg, meta))
        return "H.cb({})".format(",".join(liveview_args))


def control_element(tag, children, **attrs):
    if state.auto_id and "id_" not in attrs:
        attrs["id_"] = next(state.id_counter)
    if "id_" in attrs:
        attrs["id_"] = state.id_prefix + attrs["id_"]

    updates = {}
    as_callback_argument = None

    if state.liveview is True:
        assert attrs.get("id_"), "Needs an id to use an input with liveview."
        as_callback_argument = "H.cbs.{}('{}')".format(
            INPUT_TYPES.get(attrs.get("type_", "text"), "s"), attrs["id_"])
        for k, v in items(attrs):
            k = t(k).rstrip("_").replace("_", "-")
            if k == "meta":
                continue
            elif k.startswith("on") and type(v) in (list, tuple, Callback):
                callback = Callback(v[0], v[1:]) if type(v) in (list,
                                                                tuple) else v
                updates[k] = callback.render(as_callback_argument)
    attrs.update(updates)
    element(tag, children, **attrs)

    return Node(None, {"as_callback_argument": as_callback_argument}
                if as_callback_argument else {})


### Input ###

INPUT_TYPES = dict(checkbox="c", month="i", number="i", range="f", week="i")


def input_(**attrs):
    return control_element("input", [], void=True, **attrs)


def input_ret(**attrs):
    into = []
    node = input_(into=into, **attrs)
    return Node("".join(into), meta=node.meta)


input_.r = input_ret

### Select ###


def select_sta(*children, **attrs):
    return element_start("select", children, **attrs)


def select_end(*children, **kwargs):
    return element_end("select", children, **kwargs)


def select_ret(*children, **kwargs):
    return element_ret("select", children, **kwargs)


@contextmanager
def select_con(*children, **attrs):
    for x in element_con("select", children, **attrs):
        yield x


def select_dec(*children, **attrs):
    return element_dec("select", children, **attrs)


def select(*children, **attrs):
    return element("select", children, **attrs)


select.s = select_sta
select.e = select_end
select.r = select_ret
select.c = select_con
select.d = select_dec


### TEMPLATE-ELEMENT ###
def div_sta(*children, **attrs):
    return element_start("div", children, **attrs)


def div_end(*children, **kwargs):
    return element_end("div", children, **kwargs)


def div_ret(*children, **kwargs):
    return element_ret("div", children, **kwargs)


@contextmanager
def div_con(*children, **attrs):
    for x in element_con("div", children, **attrs):
        yield x


def div_dec(*children, **attrs):
    return element_dec("div", children, **attrs)


def div(*children, **attrs):
    return element("div", children, **attrs)


div.s = div_sta
div.e = div_end
div.r = div_ret
div.c = div_con
div.d = div_dec


### TEMPLATE-ELEMENT ###
### TEMPLATE-VOID-ELEMENT ###
def link(*children, **attrs):
    return element("link", children, void=True, **attrs)


def link_ret(*children, **attrs):
    into = []
    element("link", children, void=True, into=into, **attrs)
    return "".join(into)


link.r = link_ret

### TEMPLATE-VOID-ELEMENT ###

### RENDERED-ELEMENTS ###

### RENDERED-VOID-ELEMENTS ###

### Tests ###

if __name__ == "__main__":

    def test_div1():
        div("Hello, world!")

    assert hypergen(test_div1) == "<div>Hello, world!</div>"

    def test_div2(name):
        div("Hello",
            name,
            class_="its-hyper",
            data_x=3.14,
            hidden=True,
            selected=False,
            style={"height": 42,
                   "display": "none"},
            sep=" ",
            _sort_attrs=True)

    assert hypergen(test_div2, "hypergen!") == '<div class="its-hyper" '\
        'data-x="3.14" hidden style="display:none;height:42">'\
        'Hello hypergen!</div>'

    def test_div3():
        with div.c("div", "c", x=1, sep="."):
            div.s(1, 2, y=1, sep="-")
            div.e(5, 6, sep=" ")

    assert hypergen(test_div3) == '<div x="1">div.c<div y="1">1-25 6</div>'\
        '</div>'

    def test_div_5():
        div(None, x=1)

    assert hypergen(test_div_5) == '<div x="1"></div>'

    def test_context_manager(x):
        div("yo", blink="true")
        with div.c():
            div("12")

    assert hypergen(test_context_manager, 2) == \
        '<div blink="true">yo</div><div><div>12</div></div>'

    @div.d(1, class_="f")
    def test_decorator(x):
        div(2, 3, y=4)

    assert hypergen(test_decorator,
                    1) == '<div class="f">1<div y="4">23</div></div>'

    def test_input():
        input_(value=1, _sort_attrs=True)
        input_(value=2, id_="custom", _sort_attrs=True)
        input_(value=3, type="number", _sort_attrs=True)

    assert hypergen(test_input, id_prefix="t9") == '<input value="1"/><input '\
        'id="t9.custom" value="2"/><input type="number" value="3"/>'

    assert hypergen(test_input, id_prefix="e", liveview=True,
                    auto_id=True) == '<input '\
        'id="e.a" value="1"/><input id="e.custom" value="2"/><input '\
        'id="e.b" type="number" value="3"/>'

    def test_liveview_events():
        def callback1(x):
            pass

        callback1.hypergen_callback_url = "/hpg/cb1/"
        input_(
            value=91,
            onchange=(callback1, 9, [1], True, "foo"),
            _sort_attrs=True)

    assert hypergen(test_liveview_events, id_prefix="I", liveview=True,
                    auto_id=True) == \
        '<input id="I.a" onchange="H.cb(&quot;/hpg/cb1/&quot;,9,[1],true,&quot;'\
        'foo&quot;)" value="91"/>'

    def test_collections_as_children():
        div((div.r(x) for x in [3]), [1], (2, ))

    assert hypergen(
        test_collections_as_children) == '<div><div>3</div>12</div>'
