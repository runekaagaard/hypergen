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
                  is_form_element=False,
                  **attrs):
    def get_liveview_arg(x, attrs):
        if x == THIS:
            return json.dumps(attrs["liveview_arg"])
        else:
            arg = getattr(x, "liveview_arg", None)
            if arg:
                return json.dumps(arg)
            else:
                return json.dumps(x)

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

    def form_element(liveview, attrs):
        if state.auto_id and "id_" not in attrs:
            attrs["id_"] = next(state.id_counter)
        if "id_" in attrs:
            attrs["id_"] = state.id_prefix + attrs["id_"]
        if liveview:
            assert attrs.get(
                "id_"), "Needs an id to use an input with liveview."
            type_ = attrs.get("type_", "text")

            attrs["liveview_arg"] = [
                "H_", INPUT_TYPES.get(type_, "s"), attrs["id_"]
            ]

        return attrs

    if when is False:
        raise SkipException()

    if liveview is None:
        liveview = state.liveview

    if into is None:
        into = state.html

    attrs = copy(attrs)
    if is_form_element is True:
        attrs = form_element(liveview, attrs)

    attrs = sort_attrs(attrs)

    e = into.extend

    e(("<", tag))
    for k, v in items(attrs):
        if k == "liveview_arg": continue
        k = t(k).rstrip("_").replace("_", "-")
        if liveview and k.startswith("on") and type(v) in (list, tuple):
            assert callable(v[0]), "First arg must be a callable."
            v = "H({})".format(",".join(
                get_liveview_arg(x, attrs)
                for x in [v[0].hypergen_url] + list(v[1:])))
            e((" ", k, '="', t(v), '"'))
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

    return attrs


def element_end(tag, children, **kwargs):
    write(*children, **kwargs)
    kwargs.get("into", state.html).extend(("</", t(tag), ">"))


def element(tag, children, **attrs):
    attrs2 = element_start(tag, children, **attrs)
    if not attrs.get("void", False):
        element_end(tag, [], **attrs)

    return Bunch(attrs2)


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


### LIVEVIEW ###

THIS = "THIS_"


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


### Misc ###


def t(s, quote=True):
    return s if type(s) is Safe else escape(str(s), quote=quote)


class Safe(str):
    pass


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


class Bunch(dict):
    def __getattr__(self, k):
        return self[k]


### Input ###

INPUT_TYPES = dict(checkbox="c", month="i", number="i", range="f", week="i")


def input_(**attrs):
    return element("input", [], void=True, is_form_element=True, **attrs)


def input_ret(**attrs):
    into = []
    input_(into=into, **attrs)
    return Safe("".join(into))


input_.r = input_ret

### Select ###


def select_sta(*children, **attrs):
    return element_start("select", children, is_form_element=True, **attrs)


def select_end(*children, **kwargs):
    return element_end("select", children, is_form_element=True, **kwargs)


def select_ret(*children, **kwargs):
    return element_ret("select", children, is_form_element=True, **kwargs)


@contextmanager
def select_con(*children, **attrs):
    for x in element_con("select", children, is_form_element=True, **attrs):
        yield x


def select_dec(*children, **attrs):
    return element_dec("select", children, is_form_element=True, **attrs)


def select(*children, **attrs):
    return element("select", children, is_form_element=True, **attrs)


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


def a_sta(*children, **attrs):
    return element_start("a", children, **attrs)


def a_end(*children, **kwargs):
    return element_end("a", children, **kwargs)


def a_ret(*children, **kwargs):
    return element_ret("a", children, **kwargs)


@contextmanager
def a_con(*children, **attrs):
    for x in element_con("a", children, **attrs):
        yield x


def a_dec(*children, **attrs):
    return element_dec("a", children, **attrs)


def a(*children, **attrs):
    return element("a", children, **attrs)


a.s = a_sta
a.e = a_end
a.r = a_ret
a.c = a_con
a.d = a_dec



def abbr_sta(*children, **attrs):
    return element_start("abbr", children, **attrs)


def abbr_end(*children, **kwargs):
    return element_end("abbr", children, **kwargs)


def abbr_ret(*children, **kwargs):
    return element_ret("abbr", children, **kwargs)


@contextmanager
def abbr_con(*children, **attrs):
    for x in element_con("abbr", children, **attrs):
        yield x


def abbr_dec(*children, **attrs):
    return element_dec("abbr", children, **attrs)


def abbr(*children, **attrs):
    return element("abbr", children, **attrs)


abbr.s = abbr_sta
abbr.e = abbr_end
abbr.r = abbr_ret
abbr.c = abbr_con
abbr.d = abbr_dec



def address_sta(*children, **attrs):
    return element_start("address", children, **attrs)


def address_end(*children, **kwargs):
    return element_end("address", children, **kwargs)


def address_ret(*children, **kwargs):
    return element_ret("address", children, **kwargs)


@contextmanager
def address_con(*children, **attrs):
    for x in element_con("address", children, **attrs):
        yield x


def address_dec(*children, **attrs):
    return element_dec("address", children, **attrs)


def address(*children, **attrs):
    return element("address", children, **attrs)


address.s = address_sta
address.e = address_end
address.r = address_ret
address.c = address_con
address.d = address_dec



def article_sta(*children, **attrs):
    return element_start("article", children, **attrs)


def article_end(*children, **kwargs):
    return element_end("article", children, **kwargs)


def article_ret(*children, **kwargs):
    return element_ret("article", children, **kwargs)


@contextmanager
def article_con(*children, **attrs):
    for x in element_con("article", children, **attrs):
        yield x


def article_dec(*children, **attrs):
    return element_dec("article", children, **attrs)


def article(*children, **attrs):
    return element("article", children, **attrs)


article.s = article_sta
article.e = article_end
article.r = article_ret
article.c = article_con
article.d = article_dec



def aside_sta(*children, **attrs):
    return element_start("aside", children, **attrs)


def aside_end(*children, **kwargs):
    return element_end("aside", children, **kwargs)


def aside_ret(*children, **kwargs):
    return element_ret("aside", children, **kwargs)


@contextmanager
def aside_con(*children, **attrs):
    for x in element_con("aside", children, **attrs):
        yield x


def aside_dec(*children, **attrs):
    return element_dec("aside", children, **attrs)


def aside(*children, **attrs):
    return element("aside", children, **attrs)


aside.s = aside_sta
aside.e = aside_end
aside.r = aside_ret
aside.c = aside_con
aside.d = aside_dec



def audio_sta(*children, **attrs):
    return element_start("audio", children, **attrs)


def audio_end(*children, **kwargs):
    return element_end("audio", children, **kwargs)


def audio_ret(*children, **kwargs):
    return element_ret("audio", children, **kwargs)


@contextmanager
def audio_con(*children, **attrs):
    for x in element_con("audio", children, **attrs):
        yield x


def audio_dec(*children, **attrs):
    return element_dec("audio", children, **attrs)


def audio(*children, **attrs):
    return element("audio", children, **attrs)


audio.s = audio_sta
audio.e = audio_end
audio.r = audio_ret
audio.c = audio_con
audio.d = audio_dec



def b_sta(*children, **attrs):
    return element_start("b", children, **attrs)


def b_end(*children, **kwargs):
    return element_end("b", children, **kwargs)


def b_ret(*children, **kwargs):
    return element_ret("b", children, **kwargs)


@contextmanager
def b_con(*children, **attrs):
    for x in element_con("b", children, **attrs):
        yield x


def b_dec(*children, **attrs):
    return element_dec("b", children, **attrs)


def b(*children, **attrs):
    return element("b", children, **attrs)


b.s = b_sta
b.e = b_end
b.r = b_ret
b.c = b_con
b.d = b_dec



def bdi_sta(*children, **attrs):
    return element_start("bdi", children, **attrs)


def bdi_end(*children, **kwargs):
    return element_end("bdi", children, **kwargs)


def bdi_ret(*children, **kwargs):
    return element_ret("bdi", children, **kwargs)


@contextmanager
def bdi_con(*children, **attrs):
    for x in element_con("bdi", children, **attrs):
        yield x


def bdi_dec(*children, **attrs):
    return element_dec("bdi", children, **attrs)


def bdi(*children, **attrs):
    return element("bdi", children, **attrs)


bdi.s = bdi_sta
bdi.e = bdi_end
bdi.r = bdi_ret
bdi.c = bdi_con
bdi.d = bdi_dec



def bdo_sta(*children, **attrs):
    return element_start("bdo", children, **attrs)


def bdo_end(*children, **kwargs):
    return element_end("bdo", children, **kwargs)


def bdo_ret(*children, **kwargs):
    return element_ret("bdo", children, **kwargs)


@contextmanager
def bdo_con(*children, **attrs):
    for x in element_con("bdo", children, **attrs):
        yield x


def bdo_dec(*children, **attrs):
    return element_dec("bdo", children, **attrs)


def bdo(*children, **attrs):
    return element("bdo", children, **attrs)


bdo.s = bdo_sta
bdo.e = bdo_end
bdo.r = bdo_ret
bdo.c = bdo_con
bdo.d = bdo_dec



def blockquote_sta(*children, **attrs):
    return element_start("blockquote", children, **attrs)


def blockquote_end(*children, **kwargs):
    return element_end("blockquote", children, **kwargs)


def blockquote_ret(*children, **kwargs):
    return element_ret("blockquote", children, **kwargs)


@contextmanager
def blockquote_con(*children, **attrs):
    for x in element_con("blockquote", children, **attrs):
        yield x


def blockquote_dec(*children, **attrs):
    return element_dec("blockquote", children, **attrs)


def blockquote(*children, **attrs):
    return element("blockquote", children, **attrs)


blockquote.s = blockquote_sta
blockquote.e = blockquote_end
blockquote.r = blockquote_ret
blockquote.c = blockquote_con
blockquote.d = blockquote_dec



def body_sta(*children, **attrs):
    return element_start("body", children, **attrs)


def body_end(*children, **kwargs):
    return element_end("body", children, **kwargs)


def body_ret(*children, **kwargs):
    return element_ret("body", children, **kwargs)


@contextmanager
def body_con(*children, **attrs):
    for x in element_con("body", children, **attrs):
        yield x


def body_dec(*children, **attrs):
    return element_dec("body", children, **attrs)


def body(*children, **attrs):
    return element("body", children, **attrs)


body.s = body_sta
body.e = body_end
body.r = body_ret
body.c = body_con
body.d = body_dec



def button_sta(*children, **attrs):
    return element_start("button", children, **attrs)


def button_end(*children, **kwargs):
    return element_end("button", children, **kwargs)


def button_ret(*children, **kwargs):
    return element_ret("button", children, **kwargs)


@contextmanager
def button_con(*children, **attrs):
    for x in element_con("button", children, **attrs):
        yield x


def button_dec(*children, **attrs):
    return element_dec("button", children, **attrs)


def button(*children, **attrs):
    return element("button", children, **attrs)


button.s = button_sta
button.e = button_end
button.r = button_ret
button.c = button_con
button.d = button_dec



def canvas_sta(*children, **attrs):
    return element_start("canvas", children, **attrs)


def canvas_end(*children, **kwargs):
    return element_end("canvas", children, **kwargs)


def canvas_ret(*children, **kwargs):
    return element_ret("canvas", children, **kwargs)


@contextmanager
def canvas_con(*children, **attrs):
    for x in element_con("canvas", children, **attrs):
        yield x


def canvas_dec(*children, **attrs):
    return element_dec("canvas", children, **attrs)


def canvas(*children, **attrs):
    return element("canvas", children, **attrs)


canvas.s = canvas_sta
canvas.e = canvas_end
canvas.r = canvas_ret
canvas.c = canvas_con
canvas.d = canvas_dec



def caption_sta(*children, **attrs):
    return element_start("caption", children, **attrs)


def caption_end(*children, **kwargs):
    return element_end("caption", children, **kwargs)


def caption_ret(*children, **kwargs):
    return element_ret("caption", children, **kwargs)


@contextmanager
def caption_con(*children, **attrs):
    for x in element_con("caption", children, **attrs):
        yield x


def caption_dec(*children, **attrs):
    return element_dec("caption", children, **attrs)


def caption(*children, **attrs):
    return element("caption", children, **attrs)


caption.s = caption_sta
caption.e = caption_end
caption.r = caption_ret
caption.c = caption_con
caption.d = caption_dec



def cite_sta(*children, **attrs):
    return element_start("cite", children, **attrs)


def cite_end(*children, **kwargs):
    return element_end("cite", children, **kwargs)


def cite_ret(*children, **kwargs):
    return element_ret("cite", children, **kwargs)


@contextmanager
def cite_con(*children, **attrs):
    for x in element_con("cite", children, **attrs):
        yield x


def cite_dec(*children, **attrs):
    return element_dec("cite", children, **attrs)


def cite(*children, **attrs):
    return element("cite", children, **attrs)


cite.s = cite_sta
cite.e = cite_end
cite.r = cite_ret
cite.c = cite_con
cite.d = cite_dec



def code_sta(*children, **attrs):
    return element_start("code", children, **attrs)


def code_end(*children, **kwargs):
    return element_end("code", children, **kwargs)


def code_ret(*children, **kwargs):
    return element_ret("code", children, **kwargs)


@contextmanager
def code_con(*children, **attrs):
    for x in element_con("code", children, **attrs):
        yield x


def code_dec(*children, **attrs):
    return element_dec("code", children, **attrs)


def code(*children, **attrs):
    return element("code", children, **attrs)


code.s = code_sta
code.e = code_end
code.r = code_ret
code.c = code_con
code.d = code_dec



def colgroup_sta(*children, **attrs):
    return element_start("colgroup", children, **attrs)


def colgroup_end(*children, **kwargs):
    return element_end("colgroup", children, **kwargs)


def colgroup_ret(*children, **kwargs):
    return element_ret("colgroup", children, **kwargs)


@contextmanager
def colgroup_con(*children, **attrs):
    for x in element_con("colgroup", children, **attrs):
        yield x


def colgroup_dec(*children, **attrs):
    return element_dec("colgroup", children, **attrs)


def colgroup(*children, **attrs):
    return element("colgroup", children, **attrs)


colgroup.s = colgroup_sta
colgroup.e = colgroup_end
colgroup.r = colgroup_ret
colgroup.c = colgroup_con
colgroup.d = colgroup_dec



def datalist_sta(*children, **attrs):
    return element_start("datalist", children, **attrs)


def datalist_end(*children, **kwargs):
    return element_end("datalist", children, **kwargs)


def datalist_ret(*children, **kwargs):
    return element_ret("datalist", children, **kwargs)


@contextmanager
def datalist_con(*children, **attrs):
    for x in element_con("datalist", children, **attrs):
        yield x


def datalist_dec(*children, **attrs):
    return element_dec("datalist", children, **attrs)


def datalist(*children, **attrs):
    return element("datalist", children, **attrs)


datalist.s = datalist_sta
datalist.e = datalist_end
datalist.r = datalist_ret
datalist.c = datalist_con
datalist.d = datalist_dec



def dd_sta(*children, **attrs):
    return element_start("dd", children, **attrs)


def dd_end(*children, **kwargs):
    return element_end("dd", children, **kwargs)


def dd_ret(*children, **kwargs):
    return element_ret("dd", children, **kwargs)


@contextmanager
def dd_con(*children, **attrs):
    for x in element_con("dd", children, **attrs):
        yield x


def dd_dec(*children, **attrs):
    return element_dec("dd", children, **attrs)


def dd(*children, **attrs):
    return element("dd", children, **attrs)


dd.s = dd_sta
dd.e = dd_end
dd.r = dd_ret
dd.c = dd_con
dd.d = dd_dec



def del__sta(*children, **attrs):
    return element_start("del_", children, **attrs)


def del__end(*children, **kwargs):
    return element_end("del_", children, **kwargs)


def del__ret(*children, **kwargs):
    return element_ret("del_", children, **kwargs)


@contextmanager
def del__con(*children, **attrs):
    for x in element_con("del_", children, **attrs):
        yield x


def del__dec(*children, **attrs):
    return element_dec("del_", children, **attrs)


def del_(*children, **attrs):
    return element("del_", children, **attrs)


del_.s = del__sta
del_.e = del__end
del_.r = del__ret
del_.c = del__con
del_.d = del__dec



def details_sta(*children, **attrs):
    return element_start("details", children, **attrs)


def details_end(*children, **kwargs):
    return element_end("details", children, **kwargs)


def details_ret(*children, **kwargs):
    return element_ret("details", children, **kwargs)


@contextmanager
def details_con(*children, **attrs):
    for x in element_con("details", children, **attrs):
        yield x


def details_dec(*children, **attrs):
    return element_dec("details", children, **attrs)


def details(*children, **attrs):
    return element("details", children, **attrs)


details.s = details_sta
details.e = details_end
details.r = details_ret
details.c = details_con
details.d = details_dec



def dfn_sta(*children, **attrs):
    return element_start("dfn", children, **attrs)


def dfn_end(*children, **kwargs):
    return element_end("dfn", children, **kwargs)


def dfn_ret(*children, **kwargs):
    return element_ret("dfn", children, **kwargs)


@contextmanager
def dfn_con(*children, **attrs):
    for x in element_con("dfn", children, **attrs):
        yield x


def dfn_dec(*children, **attrs):
    return element_dec("dfn", children, **attrs)


def dfn(*children, **attrs):
    return element("dfn", children, **attrs)


dfn.s = dfn_sta
dfn.e = dfn_end
dfn.r = dfn_ret
dfn.c = dfn_con
dfn.d = dfn_dec



def dl_sta(*children, **attrs):
    return element_start("dl", children, **attrs)


def dl_end(*children, **kwargs):
    return element_end("dl", children, **kwargs)


def dl_ret(*children, **kwargs):
    return element_ret("dl", children, **kwargs)


@contextmanager
def dl_con(*children, **attrs):
    for x in element_con("dl", children, **attrs):
        yield x


def dl_dec(*children, **attrs):
    return element_dec("dl", children, **attrs)


def dl(*children, **attrs):
    return element("dl", children, **attrs)


dl.s = dl_sta
dl.e = dl_end
dl.r = dl_ret
dl.c = dl_con
dl.d = dl_dec



def dt_sta(*children, **attrs):
    return element_start("dt", children, **attrs)


def dt_end(*children, **kwargs):
    return element_end("dt", children, **kwargs)


def dt_ret(*children, **kwargs):
    return element_ret("dt", children, **kwargs)


@contextmanager
def dt_con(*children, **attrs):
    for x in element_con("dt", children, **attrs):
        yield x


def dt_dec(*children, **attrs):
    return element_dec("dt", children, **attrs)


def dt(*children, **attrs):
    return element("dt", children, **attrs)


dt.s = dt_sta
dt.e = dt_end
dt.r = dt_ret
dt.c = dt_con
dt.d = dt_dec



def em_sta(*children, **attrs):
    return element_start("em", children, **attrs)


def em_end(*children, **kwargs):
    return element_end("em", children, **kwargs)


def em_ret(*children, **kwargs):
    return element_ret("em", children, **kwargs)


@contextmanager
def em_con(*children, **attrs):
    for x in element_con("em", children, **attrs):
        yield x


def em_dec(*children, **attrs):
    return element_dec("em", children, **attrs)


def em(*children, **attrs):
    return element("em", children, **attrs)


em.s = em_sta
em.e = em_end
em.r = em_ret
em.c = em_con
em.d = em_dec



def fieldset_sta(*children, **attrs):
    return element_start("fieldset", children, **attrs)


def fieldset_end(*children, **kwargs):
    return element_end("fieldset", children, **kwargs)


def fieldset_ret(*children, **kwargs):
    return element_ret("fieldset", children, **kwargs)


@contextmanager
def fieldset_con(*children, **attrs):
    for x in element_con("fieldset", children, **attrs):
        yield x


def fieldset_dec(*children, **attrs):
    return element_dec("fieldset", children, **attrs)


def fieldset(*children, **attrs):
    return element("fieldset", children, **attrs)


fieldset.s = fieldset_sta
fieldset.e = fieldset_end
fieldset.r = fieldset_ret
fieldset.c = fieldset_con
fieldset.d = fieldset_dec



def figcaption_sta(*children, **attrs):
    return element_start("figcaption", children, **attrs)


def figcaption_end(*children, **kwargs):
    return element_end("figcaption", children, **kwargs)


def figcaption_ret(*children, **kwargs):
    return element_ret("figcaption", children, **kwargs)


@contextmanager
def figcaption_con(*children, **attrs):
    for x in element_con("figcaption", children, **attrs):
        yield x


def figcaption_dec(*children, **attrs):
    return element_dec("figcaption", children, **attrs)


def figcaption(*children, **attrs):
    return element("figcaption", children, **attrs)


figcaption.s = figcaption_sta
figcaption.e = figcaption_end
figcaption.r = figcaption_ret
figcaption.c = figcaption_con
figcaption.d = figcaption_dec



def figure_sta(*children, **attrs):
    return element_start("figure", children, **attrs)


def figure_end(*children, **kwargs):
    return element_end("figure", children, **kwargs)


def figure_ret(*children, **kwargs):
    return element_ret("figure", children, **kwargs)


@contextmanager
def figure_con(*children, **attrs):
    for x in element_con("figure", children, **attrs):
        yield x


def figure_dec(*children, **attrs):
    return element_dec("figure", children, **attrs)


def figure(*children, **attrs):
    return element("figure", children, **attrs)


figure.s = figure_sta
figure.e = figure_end
figure.r = figure_ret
figure.c = figure_con
figure.d = figure_dec



def footer_sta(*children, **attrs):
    return element_start("footer", children, **attrs)


def footer_end(*children, **kwargs):
    return element_end("footer", children, **kwargs)


def footer_ret(*children, **kwargs):
    return element_ret("footer", children, **kwargs)


@contextmanager
def footer_con(*children, **attrs):
    for x in element_con("footer", children, **attrs):
        yield x


def footer_dec(*children, **attrs):
    return element_dec("footer", children, **attrs)


def footer(*children, **attrs):
    return element("footer", children, **attrs)


footer.s = footer_sta
footer.e = footer_end
footer.r = footer_ret
footer.c = footer_con
footer.d = footer_dec



def form_sta(*children, **attrs):
    return element_start("form", children, **attrs)


def form_end(*children, **kwargs):
    return element_end("form", children, **kwargs)


def form_ret(*children, **kwargs):
    return element_ret("form", children, **kwargs)


@contextmanager
def form_con(*children, **attrs):
    for x in element_con("form", children, **attrs):
        yield x


def form_dec(*children, **attrs):
    return element_dec("form", children, **attrs)


def form(*children, **attrs):
    return element("form", children, **attrs)


form.s = form_sta
form.e = form_end
form.r = form_ret
form.c = form_con
form.d = form_dec



def h1_sta(*children, **attrs):
    return element_start("h1", children, **attrs)


def h1_end(*children, **kwargs):
    return element_end("h1", children, **kwargs)


def h1_ret(*children, **kwargs):
    return element_ret("h1", children, **kwargs)


@contextmanager
def h1_con(*children, **attrs):
    for x in element_con("h1", children, **attrs):
        yield x


def h1_dec(*children, **attrs):
    return element_dec("h1", children, **attrs)


def h1(*children, **attrs):
    return element("h1", children, **attrs)


h1.s = h1_sta
h1.e = h1_end
h1.r = h1_ret
h1.c = h1_con
h1.d = h1_dec



def h2_sta(*children, **attrs):
    return element_start("h2", children, **attrs)


def h2_end(*children, **kwargs):
    return element_end("h2", children, **kwargs)


def h2_ret(*children, **kwargs):
    return element_ret("h2", children, **kwargs)


@contextmanager
def h2_con(*children, **attrs):
    for x in element_con("h2", children, **attrs):
        yield x


def h2_dec(*children, **attrs):
    return element_dec("h2", children, **attrs)


def h2(*children, **attrs):
    return element("h2", children, **attrs)


h2.s = h2_sta
h2.e = h2_end
h2.r = h2_ret
h2.c = h2_con
h2.d = h2_dec



def h3_sta(*children, **attrs):
    return element_start("h3", children, **attrs)


def h3_end(*children, **kwargs):
    return element_end("h3", children, **kwargs)


def h3_ret(*children, **kwargs):
    return element_ret("h3", children, **kwargs)


@contextmanager
def h3_con(*children, **attrs):
    for x in element_con("h3", children, **attrs):
        yield x


def h3_dec(*children, **attrs):
    return element_dec("h3", children, **attrs)


def h3(*children, **attrs):
    return element("h3", children, **attrs)


h3.s = h3_sta
h3.e = h3_end
h3.r = h3_ret
h3.c = h3_con
h3.d = h3_dec



def h4_sta(*children, **attrs):
    return element_start("h4", children, **attrs)


def h4_end(*children, **kwargs):
    return element_end("h4", children, **kwargs)


def h4_ret(*children, **kwargs):
    return element_ret("h4", children, **kwargs)


@contextmanager
def h4_con(*children, **attrs):
    for x in element_con("h4", children, **attrs):
        yield x


def h4_dec(*children, **attrs):
    return element_dec("h4", children, **attrs)


def h4(*children, **attrs):
    return element("h4", children, **attrs)


h4.s = h4_sta
h4.e = h4_end
h4.r = h4_ret
h4.c = h4_con
h4.d = h4_dec



def h5_sta(*children, **attrs):
    return element_start("h5", children, **attrs)


def h5_end(*children, **kwargs):
    return element_end("h5", children, **kwargs)


def h5_ret(*children, **kwargs):
    return element_ret("h5", children, **kwargs)


@contextmanager
def h5_con(*children, **attrs):
    for x in element_con("h5", children, **attrs):
        yield x


def h5_dec(*children, **attrs):
    return element_dec("h5", children, **attrs)


def h5(*children, **attrs):
    return element("h5", children, **attrs)


h5.s = h5_sta
h5.e = h5_end
h5.r = h5_ret
h5.c = h5_con
h5.d = h5_dec



def h6_sta(*children, **attrs):
    return element_start("h6", children, **attrs)


def h6_end(*children, **kwargs):
    return element_end("h6", children, **kwargs)


def h6_ret(*children, **kwargs):
    return element_ret("h6", children, **kwargs)


@contextmanager
def h6_con(*children, **attrs):
    for x in element_con("h6", children, **attrs):
        yield x


def h6_dec(*children, **attrs):
    return element_dec("h6", children, **attrs)


def h6(*children, **attrs):
    return element("h6", children, **attrs)


h6.s = h6_sta
h6.e = h6_end
h6.r = h6_ret
h6.c = h6_con
h6.d = h6_dec



def header_sta(*children, **attrs):
    return element_start("header", children, **attrs)


def header_end(*children, **kwargs):
    return element_end("header", children, **kwargs)


def header_ret(*children, **kwargs):
    return element_ret("header", children, **kwargs)


@contextmanager
def header_con(*children, **attrs):
    for x in element_con("header", children, **attrs):
        yield x


def header_dec(*children, **attrs):
    return element_dec("header", children, **attrs)


def header(*children, **attrs):
    return element("header", children, **attrs)


header.s = header_sta
header.e = header_end
header.r = header_ret
header.c = header_con
header.d = header_dec



def html_sta(*children, **attrs):
    return element_start("html", children, **attrs)


def html_end(*children, **kwargs):
    return element_end("html", children, **kwargs)


def html_ret(*children, **kwargs):
    return element_ret("html", children, **kwargs)


@contextmanager
def html_con(*children, **attrs):
    for x in element_con("html", children, **attrs):
        yield x


def html_dec(*children, **attrs):
    return element_dec("html", children, **attrs)


def html(*children, **attrs):
    return element("html", children, **attrs)


html.s = html_sta
html.e = html_end
html.r = html_ret
html.c = html_con
html.d = html_dec



def i_sta(*children, **attrs):
    return element_start("i", children, **attrs)


def i_end(*children, **kwargs):
    return element_end("i", children, **kwargs)


def i_ret(*children, **kwargs):
    return element_ret("i", children, **kwargs)


@contextmanager
def i_con(*children, **attrs):
    for x in element_con("i", children, **attrs):
        yield x


def i_dec(*children, **attrs):
    return element_dec("i", children, **attrs)


def i(*children, **attrs):
    return element("i", children, **attrs)


i.s = i_sta
i.e = i_end
i.r = i_ret
i.c = i_con
i.d = i_dec



def iframe_sta(*children, **attrs):
    return element_start("iframe", children, **attrs)


def iframe_end(*children, **kwargs):
    return element_end("iframe", children, **kwargs)


def iframe_ret(*children, **kwargs):
    return element_ret("iframe", children, **kwargs)


@contextmanager
def iframe_con(*children, **attrs):
    for x in element_con("iframe", children, **attrs):
        yield x


def iframe_dec(*children, **attrs):
    return element_dec("iframe", children, **attrs)


def iframe(*children, **attrs):
    return element("iframe", children, **attrs)


iframe.s = iframe_sta
iframe.e = iframe_end
iframe.r = iframe_ret
iframe.c = iframe_con
iframe.d = iframe_dec



def ins_sta(*children, **attrs):
    return element_start("ins", children, **attrs)


def ins_end(*children, **kwargs):
    return element_end("ins", children, **kwargs)


def ins_ret(*children, **kwargs):
    return element_ret("ins", children, **kwargs)


@contextmanager
def ins_con(*children, **attrs):
    for x in element_con("ins", children, **attrs):
        yield x


def ins_dec(*children, **attrs):
    return element_dec("ins", children, **attrs)


def ins(*children, **attrs):
    return element("ins", children, **attrs)


ins.s = ins_sta
ins.e = ins_end
ins.r = ins_ret
ins.c = ins_con
ins.d = ins_dec



def kbd_sta(*children, **attrs):
    return element_start("kbd", children, **attrs)


def kbd_end(*children, **kwargs):
    return element_end("kbd", children, **kwargs)


def kbd_ret(*children, **kwargs):
    return element_ret("kbd", children, **kwargs)


@contextmanager
def kbd_con(*children, **attrs):
    for x in element_con("kbd", children, **attrs):
        yield x


def kbd_dec(*children, **attrs):
    return element_dec("kbd", children, **attrs)


def kbd(*children, **attrs):
    return element("kbd", children, **attrs)


kbd.s = kbd_sta
kbd.e = kbd_end
kbd.r = kbd_ret
kbd.c = kbd_con
kbd.d = kbd_dec



def keygen_sta(*children, **attrs):
    return element_start("keygen", children, **attrs)


def keygen_end(*children, **kwargs):
    return element_end("keygen", children, **kwargs)


def keygen_ret(*children, **kwargs):
    return element_ret("keygen", children, **kwargs)


@contextmanager
def keygen_con(*children, **attrs):
    for x in element_con("keygen", children, **attrs):
        yield x


def keygen_dec(*children, **attrs):
    return element_dec("keygen", children, **attrs)


def keygen(*children, **attrs):
    return element("keygen", children, **attrs)


keygen.s = keygen_sta
keygen.e = keygen_end
keygen.r = keygen_ret
keygen.c = keygen_con
keygen.d = keygen_dec



def label_sta(*children, **attrs):
    return element_start("label", children, **attrs)


def label_end(*children, **kwargs):
    return element_end("label", children, **kwargs)


def label_ret(*children, **kwargs):
    return element_ret("label", children, **kwargs)


@contextmanager
def label_con(*children, **attrs):
    for x in element_con("label", children, **attrs):
        yield x


def label_dec(*children, **attrs):
    return element_dec("label", children, **attrs)


def label(*children, **attrs):
    return element("label", children, **attrs)


label.s = label_sta
label.e = label_end
label.r = label_ret
label.c = label_con
label.d = label_dec



def legend_sta(*children, **attrs):
    return element_start("legend", children, **attrs)


def legend_end(*children, **kwargs):
    return element_end("legend", children, **kwargs)


def legend_ret(*children, **kwargs):
    return element_ret("legend", children, **kwargs)


@contextmanager
def legend_con(*children, **attrs):
    for x in element_con("legend", children, **attrs):
        yield x


def legend_dec(*children, **attrs):
    return element_dec("legend", children, **attrs)


def legend(*children, **attrs):
    return element("legend", children, **attrs)


legend.s = legend_sta
legend.e = legend_end
legend.r = legend_ret
legend.c = legend_con
legend.d = legend_dec



def li_sta(*children, **attrs):
    return element_start("li", children, **attrs)


def li_end(*children, **kwargs):
    return element_end("li", children, **kwargs)


def li_ret(*children, **kwargs):
    return element_ret("li", children, **kwargs)


@contextmanager
def li_con(*children, **attrs):
    for x in element_con("li", children, **attrs):
        yield x


def li_dec(*children, **attrs):
    return element_dec("li", children, **attrs)


def li(*children, **attrs):
    return element("li", children, **attrs)


li.s = li_sta
li.e = li_end
li.r = li_ret
li.c = li_con
li.d = li_dec



def main_sta(*children, **attrs):
    return element_start("main", children, **attrs)


def main_end(*children, **kwargs):
    return element_end("main", children, **kwargs)


def main_ret(*children, **kwargs):
    return element_ret("main", children, **kwargs)


@contextmanager
def main_con(*children, **attrs):
    for x in element_con("main", children, **attrs):
        yield x


def main_dec(*children, **attrs):
    return element_dec("main", children, **attrs)


def main(*children, **attrs):
    return element("main", children, **attrs)


main.s = main_sta
main.e = main_end
main.r = main_ret
main.c = main_con
main.d = main_dec



def map_sta(*children, **attrs):
    return element_start("map", children, **attrs)


def map_end(*children, **kwargs):
    return element_end("map", children, **kwargs)


def map_ret(*children, **kwargs):
    return element_ret("map", children, **kwargs)


@contextmanager
def map_con(*children, **attrs):
    for x in element_con("map", children, **attrs):
        yield x


def map_dec(*children, **attrs):
    return element_dec("map", children, **attrs)


def map(*children, **attrs):
    return element("map", children, **attrs)


map.s = map_sta
map.e = map_end
map.r = map_ret
map.c = map_con
map.d = map_dec



def mark_sta(*children, **attrs):
    return element_start("mark", children, **attrs)


def mark_end(*children, **kwargs):
    return element_end("mark", children, **kwargs)


def mark_ret(*children, **kwargs):
    return element_ret("mark", children, **kwargs)


@contextmanager
def mark_con(*children, **attrs):
    for x in element_con("mark", children, **attrs):
        yield x


def mark_dec(*children, **attrs):
    return element_dec("mark", children, **attrs)


def mark(*children, **attrs):
    return element("mark", children, **attrs)


mark.s = mark_sta
mark.e = mark_end
mark.r = mark_ret
mark.c = mark_con
mark.d = mark_dec



def menu_sta(*children, **attrs):
    return element_start("menu", children, **attrs)


def menu_end(*children, **kwargs):
    return element_end("menu", children, **kwargs)


def menu_ret(*children, **kwargs):
    return element_ret("menu", children, **kwargs)


@contextmanager
def menu_con(*children, **attrs):
    for x in element_con("menu", children, **attrs):
        yield x


def menu_dec(*children, **attrs):
    return element_dec("menu", children, **attrs)


def menu(*children, **attrs):
    return element("menu", children, **attrs)


menu.s = menu_sta
menu.e = menu_end
menu.r = menu_ret
menu.c = menu_con
menu.d = menu_dec



def meter_sta(*children, **attrs):
    return element_start("meter", children, **attrs)


def meter_end(*children, **kwargs):
    return element_end("meter", children, **kwargs)


def meter_ret(*children, **kwargs):
    return element_ret("meter", children, **kwargs)


@contextmanager
def meter_con(*children, **attrs):
    for x in element_con("meter", children, **attrs):
        yield x


def meter_dec(*children, **attrs):
    return element_dec("meter", children, **attrs)


def meter(*children, **attrs):
    return element("meter", children, **attrs)


meter.s = meter_sta
meter.e = meter_end
meter.r = meter_ret
meter.c = meter_con
meter.d = meter_dec



def nav_sta(*children, **attrs):
    return element_start("nav", children, **attrs)


def nav_end(*children, **kwargs):
    return element_end("nav", children, **kwargs)


def nav_ret(*children, **kwargs):
    return element_ret("nav", children, **kwargs)


@contextmanager
def nav_con(*children, **attrs):
    for x in element_con("nav", children, **attrs):
        yield x


def nav_dec(*children, **attrs):
    return element_dec("nav", children, **attrs)


def nav(*children, **attrs):
    return element("nav", children, **attrs)


nav.s = nav_sta
nav.e = nav_end
nav.r = nav_ret
nav.c = nav_con
nav.d = nav_dec



def object_sta(*children, **attrs):
    return element_start("object", children, **attrs)


def object_end(*children, **kwargs):
    return element_end("object", children, **kwargs)


def object_ret(*children, **kwargs):
    return element_ret("object", children, **kwargs)


@contextmanager
def object_con(*children, **attrs):
    for x in element_con("object", children, **attrs):
        yield x


def object_dec(*children, **attrs):
    return element_dec("object", children, **attrs)


def object(*children, **attrs):
    return element("object", children, **attrs)


object.s = object_sta
object.e = object_end
object.r = object_ret
object.c = object_con
object.d = object_dec



def ol_sta(*children, **attrs):
    return element_start("ol", children, **attrs)


def ol_end(*children, **kwargs):
    return element_end("ol", children, **kwargs)


def ol_ret(*children, **kwargs):
    return element_ret("ol", children, **kwargs)


@contextmanager
def ol_con(*children, **attrs):
    for x in element_con("ol", children, **attrs):
        yield x


def ol_dec(*children, **attrs):
    return element_dec("ol", children, **attrs)


def ol(*children, **attrs):
    return element("ol", children, **attrs)


ol.s = ol_sta
ol.e = ol_end
ol.r = ol_ret
ol.c = ol_con
ol.d = ol_dec



def optgroup_sta(*children, **attrs):
    return element_start("optgroup", children, **attrs)


def optgroup_end(*children, **kwargs):
    return element_end("optgroup", children, **kwargs)


def optgroup_ret(*children, **kwargs):
    return element_ret("optgroup", children, **kwargs)


@contextmanager
def optgroup_con(*children, **attrs):
    for x in element_con("optgroup", children, **attrs):
        yield x


def optgroup_dec(*children, **attrs):
    return element_dec("optgroup", children, **attrs)


def optgroup(*children, **attrs):
    return element("optgroup", children, **attrs)


optgroup.s = optgroup_sta
optgroup.e = optgroup_end
optgroup.r = optgroup_ret
optgroup.c = optgroup_con
optgroup.d = optgroup_dec



def option_sta(*children, **attrs):
    return element_start("option", children, **attrs)


def option_end(*children, **kwargs):
    return element_end("option", children, **kwargs)


def option_ret(*children, **kwargs):
    return element_ret("option", children, **kwargs)


@contextmanager
def option_con(*children, **attrs):
    for x in element_con("option", children, **attrs):
        yield x


def option_dec(*children, **attrs):
    return element_dec("option", children, **attrs)


def option(*children, **attrs):
    return element("option", children, **attrs)


option.s = option_sta
option.e = option_end
option.r = option_ret
option.c = option_con
option.d = option_dec



def output_sta(*children, **attrs):
    return element_start("output", children, **attrs)


def output_end(*children, **kwargs):
    return element_end("output", children, **kwargs)


def output_ret(*children, **kwargs):
    return element_ret("output", children, **kwargs)


@contextmanager
def output_con(*children, **attrs):
    for x in element_con("output", children, **attrs):
        yield x


def output_dec(*children, **attrs):
    return element_dec("output", children, **attrs)


def output(*children, **attrs):
    return element("output", children, **attrs)


output.s = output_sta
output.e = output_end
output.r = output_ret
output.c = output_con
output.d = output_dec



def p_sta(*children, **attrs):
    return element_start("p", children, **attrs)


def p_end(*children, **kwargs):
    return element_end("p", children, **kwargs)


def p_ret(*children, **kwargs):
    return element_ret("p", children, **kwargs)


@contextmanager
def p_con(*children, **attrs):
    for x in element_con("p", children, **attrs):
        yield x


def p_dec(*children, **attrs):
    return element_dec("p", children, **attrs)


def p(*children, **attrs):
    return element("p", children, **attrs)


p.s = p_sta
p.e = p_end
p.r = p_ret
p.c = p_con
p.d = p_dec



def pre_sta(*children, **attrs):
    return element_start("pre", children, **attrs)


def pre_end(*children, **kwargs):
    return element_end("pre", children, **kwargs)


def pre_ret(*children, **kwargs):
    return element_ret("pre", children, **kwargs)


@contextmanager
def pre_con(*children, **attrs):
    for x in element_con("pre", children, **attrs):
        yield x


def pre_dec(*children, **attrs):
    return element_dec("pre", children, **attrs)


def pre(*children, **attrs):
    return element("pre", children, **attrs)


pre.s = pre_sta
pre.e = pre_end
pre.r = pre_ret
pre.c = pre_con
pre.d = pre_dec



def progress_sta(*children, **attrs):
    return element_start("progress", children, **attrs)


def progress_end(*children, **kwargs):
    return element_end("progress", children, **kwargs)


def progress_ret(*children, **kwargs):
    return element_ret("progress", children, **kwargs)


@contextmanager
def progress_con(*children, **attrs):
    for x in element_con("progress", children, **attrs):
        yield x


def progress_dec(*children, **attrs):
    return element_dec("progress", children, **attrs)


def progress(*children, **attrs):
    return element("progress", children, **attrs)


progress.s = progress_sta
progress.e = progress_end
progress.r = progress_ret
progress.c = progress_con
progress.d = progress_dec



def q_sta(*children, **attrs):
    return element_start("q", children, **attrs)


def q_end(*children, **kwargs):
    return element_end("q", children, **kwargs)


def q_ret(*children, **kwargs):
    return element_ret("q", children, **kwargs)


@contextmanager
def q_con(*children, **attrs):
    for x in element_con("q", children, **attrs):
        yield x


def q_dec(*children, **attrs):
    return element_dec("q", children, **attrs)


def q(*children, **attrs):
    return element("q", children, **attrs)


q.s = q_sta
q.e = q_end
q.r = q_ret
q.c = q_con
q.d = q_dec



def rp_sta(*children, **attrs):
    return element_start("rp", children, **attrs)


def rp_end(*children, **kwargs):
    return element_end("rp", children, **kwargs)


def rp_ret(*children, **kwargs):
    return element_ret("rp", children, **kwargs)


@contextmanager
def rp_con(*children, **attrs):
    for x in element_con("rp", children, **attrs):
        yield x


def rp_dec(*children, **attrs):
    return element_dec("rp", children, **attrs)


def rp(*children, **attrs):
    return element("rp", children, **attrs)


rp.s = rp_sta
rp.e = rp_end
rp.r = rp_ret
rp.c = rp_con
rp.d = rp_dec



def rt_sta(*children, **attrs):
    return element_start("rt", children, **attrs)


def rt_end(*children, **kwargs):
    return element_end("rt", children, **kwargs)


def rt_ret(*children, **kwargs):
    return element_ret("rt", children, **kwargs)


@contextmanager
def rt_con(*children, **attrs):
    for x in element_con("rt", children, **attrs):
        yield x


def rt_dec(*children, **attrs):
    return element_dec("rt", children, **attrs)


def rt(*children, **attrs):
    return element("rt", children, **attrs)


rt.s = rt_sta
rt.e = rt_end
rt.r = rt_ret
rt.c = rt_con
rt.d = rt_dec



def ruby_sta(*children, **attrs):
    return element_start("ruby", children, **attrs)


def ruby_end(*children, **kwargs):
    return element_end("ruby", children, **kwargs)


def ruby_ret(*children, **kwargs):
    return element_ret("ruby", children, **kwargs)


@contextmanager
def ruby_con(*children, **attrs):
    for x in element_con("ruby", children, **attrs):
        yield x


def ruby_dec(*children, **attrs):
    return element_dec("ruby", children, **attrs)


def ruby(*children, **attrs):
    return element("ruby", children, **attrs)


ruby.s = ruby_sta
ruby.e = ruby_end
ruby.r = ruby_ret
ruby.c = ruby_con
ruby.d = ruby_dec



def s_sta(*children, **attrs):
    return element_start("s", children, **attrs)


def s_end(*children, **kwargs):
    return element_end("s", children, **kwargs)


def s_ret(*children, **kwargs):
    return element_ret("s", children, **kwargs)


@contextmanager
def s_con(*children, **attrs):
    for x in element_con("s", children, **attrs):
        yield x


def s_dec(*children, **attrs):
    return element_dec("s", children, **attrs)


def s(*children, **attrs):
    return element("s", children, **attrs)


s.s = s_sta
s.e = s_end
s.r = s_ret
s.c = s_con
s.d = s_dec



def samp_sta(*children, **attrs):
    return element_start("samp", children, **attrs)


def samp_end(*children, **kwargs):
    return element_end("samp", children, **kwargs)


def samp_ret(*children, **kwargs):
    return element_ret("samp", children, **kwargs)


@contextmanager
def samp_con(*children, **attrs):
    for x in element_con("samp", children, **attrs):
        yield x


def samp_dec(*children, **attrs):
    return element_dec("samp", children, **attrs)


def samp(*children, **attrs):
    return element("samp", children, **attrs)


samp.s = samp_sta
samp.e = samp_end
samp.r = samp_ret
samp.c = samp_con
samp.d = samp_dec



def section_sta(*children, **attrs):
    return element_start("section", children, **attrs)


def section_end(*children, **kwargs):
    return element_end("section", children, **kwargs)


def section_ret(*children, **kwargs):
    return element_ret("section", children, **kwargs)


@contextmanager
def section_con(*children, **attrs):
    for x in element_con("section", children, **attrs):
        yield x


def section_dec(*children, **attrs):
    return element_dec("section", children, **attrs)


def section(*children, **attrs):
    return element("section", children, **attrs)


section.s = section_sta
section.e = section_end
section.r = section_ret
section.c = section_con
section.d = section_dec



def small_sta(*children, **attrs):
    return element_start("small", children, **attrs)


def small_end(*children, **kwargs):
    return element_end("small", children, **kwargs)


def small_ret(*children, **kwargs):
    return element_ret("small", children, **kwargs)


@contextmanager
def small_con(*children, **attrs):
    for x in element_con("small", children, **attrs):
        yield x


def small_dec(*children, **attrs):
    return element_dec("small", children, **attrs)


def small(*children, **attrs):
    return element("small", children, **attrs)


small.s = small_sta
small.e = small_end
small.r = small_ret
small.c = small_con
small.d = small_dec



def span_sta(*children, **attrs):
    return element_start("span", children, **attrs)


def span_end(*children, **kwargs):
    return element_end("span", children, **kwargs)


def span_ret(*children, **kwargs):
    return element_ret("span", children, **kwargs)


@contextmanager
def span_con(*children, **attrs):
    for x in element_con("span", children, **attrs):
        yield x


def span_dec(*children, **attrs):
    return element_dec("span", children, **attrs)


def span(*children, **attrs):
    return element("span", children, **attrs)


span.s = span_sta
span.e = span_end
span.r = span_ret
span.c = span_con
span.d = span_dec



def strong_sta(*children, **attrs):
    return element_start("strong", children, **attrs)


def strong_end(*children, **kwargs):
    return element_end("strong", children, **kwargs)


def strong_ret(*children, **kwargs):
    return element_ret("strong", children, **kwargs)


@contextmanager
def strong_con(*children, **attrs):
    for x in element_con("strong", children, **attrs):
        yield x


def strong_dec(*children, **attrs):
    return element_dec("strong", children, **attrs)


def strong(*children, **attrs):
    return element("strong", children, **attrs)


strong.s = strong_sta
strong.e = strong_end
strong.r = strong_ret
strong.c = strong_con
strong.d = strong_dec



def sub_sta(*children, **attrs):
    return element_start("sub", children, **attrs)


def sub_end(*children, **kwargs):
    return element_end("sub", children, **kwargs)


def sub_ret(*children, **kwargs):
    return element_ret("sub", children, **kwargs)


@contextmanager
def sub_con(*children, **attrs):
    for x in element_con("sub", children, **attrs):
        yield x


def sub_dec(*children, **attrs):
    return element_dec("sub", children, **attrs)


def sub(*children, **attrs):
    return element("sub", children, **attrs)


sub.s = sub_sta
sub.e = sub_end
sub.r = sub_ret
sub.c = sub_con
sub.d = sub_dec



def summary_sta(*children, **attrs):
    return element_start("summary", children, **attrs)


def summary_end(*children, **kwargs):
    return element_end("summary", children, **kwargs)


def summary_ret(*children, **kwargs):
    return element_ret("summary", children, **kwargs)


@contextmanager
def summary_con(*children, **attrs):
    for x in element_con("summary", children, **attrs):
        yield x


def summary_dec(*children, **attrs):
    return element_dec("summary", children, **attrs)


def summary(*children, **attrs):
    return element("summary", children, **attrs)


summary.s = summary_sta
summary.e = summary_end
summary.r = summary_ret
summary.c = summary_con
summary.d = summary_dec



def sup_sta(*children, **attrs):
    return element_start("sup", children, **attrs)


def sup_end(*children, **kwargs):
    return element_end("sup", children, **kwargs)


def sup_ret(*children, **kwargs):
    return element_ret("sup", children, **kwargs)


@contextmanager
def sup_con(*children, **attrs):
    for x in element_con("sup", children, **attrs):
        yield x


def sup_dec(*children, **attrs):
    return element_dec("sup", children, **attrs)


def sup(*children, **attrs):
    return element("sup", children, **attrs)


sup.s = sup_sta
sup.e = sup_end
sup.r = sup_ret
sup.c = sup_con
sup.d = sup_dec



def table_sta(*children, **attrs):
    return element_start("table", children, **attrs)


def table_end(*children, **kwargs):
    return element_end("table", children, **kwargs)


def table_ret(*children, **kwargs):
    return element_ret("table", children, **kwargs)


@contextmanager
def table_con(*children, **attrs):
    for x in element_con("table", children, **attrs):
        yield x


def table_dec(*children, **attrs):
    return element_dec("table", children, **attrs)


def table(*children, **attrs):
    return element("table", children, **attrs)


table.s = table_sta
table.e = table_end
table.r = table_ret
table.c = table_con
table.d = table_dec



def tbody_sta(*children, **attrs):
    return element_start("tbody", children, **attrs)


def tbody_end(*children, **kwargs):
    return element_end("tbody", children, **kwargs)


def tbody_ret(*children, **kwargs):
    return element_ret("tbody", children, **kwargs)


@contextmanager
def tbody_con(*children, **attrs):
    for x in element_con("tbody", children, **attrs):
        yield x


def tbody_dec(*children, **attrs):
    return element_dec("tbody", children, **attrs)


def tbody(*children, **attrs):
    return element("tbody", children, **attrs)


tbody.s = tbody_sta
tbody.e = tbody_end
tbody.r = tbody_ret
tbody.c = tbody_con
tbody.d = tbody_dec



def td_sta(*children, **attrs):
    return element_start("td", children, **attrs)


def td_end(*children, **kwargs):
    return element_end("td", children, **kwargs)


def td_ret(*children, **kwargs):
    return element_ret("td", children, **kwargs)


@contextmanager
def td_con(*children, **attrs):
    for x in element_con("td", children, **attrs):
        yield x


def td_dec(*children, **attrs):
    return element_dec("td", children, **attrs)


def td(*children, **attrs):
    return element("td", children, **attrs)


td.s = td_sta
td.e = td_end
td.r = td_ret
td.c = td_con
td.d = td_dec



def textarea_sta(*children, **attrs):
    return element_start("textarea", children, **attrs)


def textarea_end(*children, **kwargs):
    return element_end("textarea", children, **kwargs)


def textarea_ret(*children, **kwargs):
    return element_ret("textarea", children, **kwargs)


@contextmanager
def textarea_con(*children, **attrs):
    for x in element_con("textarea", children, **attrs):
        yield x


def textarea_dec(*children, **attrs):
    return element_dec("textarea", children, **attrs)


def textarea(*children, **attrs):
    return element("textarea", children, **attrs)


textarea.s = textarea_sta
textarea.e = textarea_end
textarea.r = textarea_ret
textarea.c = textarea_con
textarea.d = textarea_dec



def tfoot_sta(*children, **attrs):
    return element_start("tfoot", children, **attrs)


def tfoot_end(*children, **kwargs):
    return element_end("tfoot", children, **kwargs)


def tfoot_ret(*children, **kwargs):
    return element_ret("tfoot", children, **kwargs)


@contextmanager
def tfoot_con(*children, **attrs):
    for x in element_con("tfoot", children, **attrs):
        yield x


def tfoot_dec(*children, **attrs):
    return element_dec("tfoot", children, **attrs)


def tfoot(*children, **attrs):
    return element("tfoot", children, **attrs)


tfoot.s = tfoot_sta
tfoot.e = tfoot_end
tfoot.r = tfoot_ret
tfoot.c = tfoot_con
tfoot.d = tfoot_dec



def th_sta(*children, **attrs):
    return element_start("th", children, **attrs)


def th_end(*children, **kwargs):
    return element_end("th", children, **kwargs)


def th_ret(*children, **kwargs):
    return element_ret("th", children, **kwargs)


@contextmanager
def th_con(*children, **attrs):
    for x in element_con("th", children, **attrs):
        yield x


def th_dec(*children, **attrs):
    return element_dec("th", children, **attrs)


def th(*children, **attrs):
    return element("th", children, **attrs)


th.s = th_sta
th.e = th_end
th.r = th_ret
th.c = th_con
th.d = th_dec



def thead_sta(*children, **attrs):
    return element_start("thead", children, **attrs)


def thead_end(*children, **kwargs):
    return element_end("thead", children, **kwargs)


def thead_ret(*children, **kwargs):
    return element_ret("thead", children, **kwargs)


@contextmanager
def thead_con(*children, **attrs):
    for x in element_con("thead", children, **attrs):
        yield x


def thead_dec(*children, **attrs):
    return element_dec("thead", children, **attrs)


def thead(*children, **attrs):
    return element("thead", children, **attrs)


thead.s = thead_sta
thead.e = thead_end
thead.r = thead_ret
thead.c = thead_con
thead.d = thead_dec



def time_sta(*children, **attrs):
    return element_start("time", children, **attrs)


def time_end(*children, **kwargs):
    return element_end("time", children, **kwargs)


def time_ret(*children, **kwargs):
    return element_ret("time", children, **kwargs)


@contextmanager
def time_con(*children, **attrs):
    for x in element_con("time", children, **attrs):
        yield x


def time_dec(*children, **attrs):
    return element_dec("time", children, **attrs)


def time(*children, **attrs):
    return element("time", children, **attrs)


time.s = time_sta
time.e = time_end
time.r = time_ret
time.c = time_con
time.d = time_dec



def tr_sta(*children, **attrs):
    return element_start("tr", children, **attrs)


def tr_end(*children, **kwargs):
    return element_end("tr", children, **kwargs)


def tr_ret(*children, **kwargs):
    return element_ret("tr", children, **kwargs)


@contextmanager
def tr_con(*children, **attrs):
    for x in element_con("tr", children, **attrs):
        yield x


def tr_dec(*children, **attrs):
    return element_dec("tr", children, **attrs)


def tr(*children, **attrs):
    return element("tr", children, **attrs)


tr.s = tr_sta
tr.e = tr_end
tr.r = tr_ret
tr.c = tr_con
tr.d = tr_dec



def u_sta(*children, **attrs):
    return element_start("u", children, **attrs)


def u_end(*children, **kwargs):
    return element_end("u", children, **kwargs)


def u_ret(*children, **kwargs):
    return element_ret("u", children, **kwargs)


@contextmanager
def u_con(*children, **attrs):
    for x in element_con("u", children, **attrs):
        yield x


def u_dec(*children, **attrs):
    return element_dec("u", children, **attrs)


def u(*children, **attrs):
    return element("u", children, **attrs)


u.s = u_sta
u.e = u_end
u.r = u_ret
u.c = u_con
u.d = u_dec



def ul_sta(*children, **attrs):
    return element_start("ul", children, **attrs)


def ul_end(*children, **kwargs):
    return element_end("ul", children, **kwargs)


def ul_ret(*children, **kwargs):
    return element_ret("ul", children, **kwargs)


@contextmanager
def ul_con(*children, **attrs):
    for x in element_con("ul", children, **attrs):
        yield x


def ul_dec(*children, **attrs):
    return element_dec("ul", children, **attrs)


def ul(*children, **attrs):
    return element("ul", children, **attrs)


ul.s = ul_sta
ul.e = ul_end
ul.r = ul_ret
ul.c = ul_con
ul.d = ul_dec



def var_sta(*children, **attrs):
    return element_start("var", children, **attrs)


def var_end(*children, **kwargs):
    return element_end("var", children, **kwargs)


def var_ret(*children, **kwargs):
    return element_ret("var", children, **kwargs)


@contextmanager
def var_con(*children, **attrs):
    for x in element_con("var", children, **attrs):
        yield x


def var_dec(*children, **attrs):
    return element_dec("var", children, **attrs)


def var(*children, **attrs):
    return element("var", children, **attrs)


var.s = var_sta
var.e = var_end
var.r = var_ret
var.c = var_con
var.d = var_dec



def video_sta(*children, **attrs):
    return element_start("video", children, **attrs)


def video_end(*children, **kwargs):
    return element_end("video", children, **kwargs)


def video_ret(*children, **kwargs):
    return element_ret("video", children, **kwargs)


@contextmanager
def video_con(*children, **attrs):
    for x in element_con("video", children, **attrs):
        yield x


def video_dec(*children, **attrs):
    return element_dec("video", children, **attrs)


def video(*children, **attrs):
    return element("video", children, **attrs)


video.s = video_sta
video.e = video_end
video.r = video_ret
video.c = video_con
video.d = video_dec



def script_sta(*children, **attrs):
    return element_start("script", children, **attrs)


def script_end(*children, **kwargs):
    return element_end("script", children, **kwargs)


def script_ret(*children, **kwargs):
    return element_ret("script", children, **kwargs)


@contextmanager
def script_con(*children, **attrs):
    for x in element_con("script", children, **attrs):
        yield x


def script_dec(*children, **attrs):
    return element_dec("script", children, **attrs)


def script(*children, **attrs):
    return element("script", children, **attrs)


script.s = script_sta
script.e = script_end
script.r = script_ret
script.c = script_con
script.d = script_dec



def style_sta(*children, **attrs):
    return element_start("style", children, **attrs)


def style_end(*children, **kwargs):
    return element_end("style", children, **kwargs)


def style_ret(*children, **kwargs):
    return element_ret("style", children, **kwargs)


@contextmanager
def style_con(*children, **attrs):
    for x in element_con("style", children, **attrs):
        yield x


def style_dec(*children, **attrs):
    return element_dec("style", children, **attrs)


def style(*children, **attrs):
    return element("style", children, **attrs)


style.s = style_sta
style.e = style_end
style.r = style_ret
style.c = style_con
style.d = style_dec



def html_sta(*children, **attrs):
    return element_start("html", children, **attrs)


def html_end(*children, **kwargs):
    return element_end("html", children, **kwargs)


def html_ret(*children, **kwargs):
    return element_ret("html", children, **kwargs)


@contextmanager
def html_con(*children, **attrs):
    for x in element_con("html", children, **attrs):
        yield x


def html_dec(*children, **attrs):
    return element_dec("html", children, **attrs)


def html(*children, **attrs):
    return element("html", children, **attrs)


html.s = html_sta
html.e = html_end
html.r = html_ret
html.c = html_con
html.d = html_dec



def body_sta(*children, **attrs):
    return element_start("body", children, **attrs)


def body_end(*children, **kwargs):
    return element_end("body", children, **kwargs)


def body_ret(*children, **kwargs):
    return element_ret("body", children, **kwargs)


@contextmanager
def body_con(*children, **attrs):
    for x in element_con("body", children, **attrs):
        yield x


def body_dec(*children, **attrs):
    return element_dec("body", children, **attrs)


def body(*children, **attrs):
    return element("body", children, **attrs)


body.s = body_sta
body.e = body_end
body.r = body_ret
body.c = body_con
body.d = body_dec



def head_sta(*children, **attrs):
    return element_start("head", children, **attrs)


def head_end(*children, **kwargs):
    return element_end("head", children, **kwargs)


def head_ret(*children, **kwargs):
    return element_ret("head", children, **kwargs)


@contextmanager
def head_con(*children, **attrs):
    for x in element_con("head", children, **attrs):
        yield x


def head_dec(*children, **attrs):
    return element_dec("head", children, **attrs)


def head(*children, **attrs):
    return element("head", children, **attrs)


head.s = head_sta
head.e = head_end
head.r = head_ret
head.c = head_con
head.d = head_dec





def area(*children, **attrs):
    return element("area", children, void=True, **attrs)


def area_ret(*children, **attrs):
    into = []
    element("area", children, void=True, into=into, **attrs)
    return "".join(into)


area.r = area_ret


def base(*children, **attrs):
    return element("base", children, void=True, **attrs)


def base_ret(*children, **attrs):
    into = []
    element("base", children, void=True, into=into, **attrs)
    return "".join(into)


base.r = base_ret


def br(*children, **attrs):
    return element("br", children, void=True, **attrs)


def br_ret(*children, **attrs):
    into = []
    element("br", children, void=True, into=into, **attrs)
    return "".join(into)


br.r = br_ret


def col(*children, **attrs):
    return element("col", children, void=True, **attrs)


def col_ret(*children, **attrs):
    into = []
    element("col", children, void=True, into=into, **attrs)
    return "".join(into)


col.r = col_ret


def embed(*children, **attrs):
    return element("embed", children, void=True, **attrs)


def embed_ret(*children, **attrs):
    into = []
    element("embed", children, void=True, into=into, **attrs)
    return "".join(into)


embed.r = embed_ret


def hr(*children, **attrs):
    return element("hr", children, void=True, **attrs)


def hr_ret(*children, **attrs):
    into = []
    element("hr", children, void=True, into=into, **attrs)
    return "".join(into)


hr.r = hr_ret


def img(*children, **attrs):
    return element("img", children, void=True, **attrs)


def img_ret(*children, **attrs):
    into = []
    element("img", children, void=True, into=into, **attrs)
    return "".join(into)


img.r = img_ret


def meta(*children, **attrs):
    return element("meta", children, void=True, **attrs)


def meta_ret(*children, **attrs):
    into = []
    element("meta", children, void=True, into=into, **attrs)
    return "".join(into)


meta.r = meta_ret


def param(*children, **attrs):
    return element("param", children, void=True, **attrs)


def param_ret(*children, **attrs):
    into = []
    element("param", children, void=True, into=into, **attrs)
    return "".join(into)


param.r = param_ret


def source(*children, **attrs):
    return element("source", children, void=True, **attrs)


def source_ret(*children, **attrs):
    into = []
    element("source", children, void=True, into=into, **attrs)
    return "".join(into)


source.r = source_ret


def track(*children, **attrs):
    return element("track", children, void=True, **attrs)


def track_ret(*children, **attrs):
    into = []
    element("track", children, void=True, into=into, **attrs)
    return "".join(into)


track.r = track_ret


def wbr(*children, **attrs):
    return element("wbr", children, void=True, **attrs)


def wbr_ret(*children, **attrs):
    into = []
    element("wbr", children, void=True, into=into, **attrs)
    return "".join(into)


wbr.r = wbr_ret


def command(*children, **attrs):
    return element("command", children, void=True, **attrs)


def command_ret(*children, **attrs):
    into = []
    element("command", children, void=True, into=into, **attrs)
    return "".join(into)


command.r = command_ret


def keygen(*children, **attrs):
    return element("keygen", children, void=True, **attrs)


def keygen_ret(*children, **attrs):
    into = []
    element("keygen", children, void=True, into=into, **attrs)
    return "".join(into)


keygen.r = keygen_ret


def menuitem(*children, **attrs):
    return element("menuitem", children, void=True, **attrs)


def menuitem_ret(*children, **attrs):
    into = []
    element("menuitem", children, void=True, into=into, **attrs)
    return "".join(into)


menuitem.r = menuitem_ret



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

        callback1.hypergen_url = "/hpg/cb1/"
        input_(
            value=91,
            onchange=(callback1, 9, [1], True, "foo"),
            _sort_attrs=True)
    assert hypergen(test_liveview_events, id_prefix="I", liveview=True,
                    auto_id=True) == \
        '<input id="I.a" onchange="H(&quot;/hpg/cb1/&quot;,9,[1],true,&quot;'\
        'foo&quot;)" value="91"/>'

    def test_collections_as_children():
        div((div.r(x) for x in [3]), [1], (2, ))

    assert hypergen(
        test_collections_as_children) == '<div><div>3</div>12</div>'
