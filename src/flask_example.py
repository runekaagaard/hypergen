# To run, pip install flask, and then
#     FLASK_ENV=development FLASK_APP=flask_example flask run

from functools import partial

from flask import Flask, url_for
from hypergen import (flask_liveview_hypergen as hypergen,
                      flask_liveview_callback_route as callback_route, div,
                      input_, script, raw, label, p, h1, ul, li, a, html, head,
                      body, link, table, tr, th, td, THIS, pre)

NORMALISE = "https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css"
SAKURA = "https://unpkg.com/sakura.css/css/sakura.css"
JQUERY = "https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"

app = Flask(__name__)
i = 0


def base_template(content_func):
    raw("<!DOCTYPE html>")
    with html():
        with head():
            link(href=NORMALISE, rel="stylesheet", type_="text/css")
            link(href=SAKURA, rel="stylesheet", type_="text/css")
            script(src=JQUERY)
            with script(), open("hypergen.js") as f:
                raw(f.read())

        with body():
            div(a.r("Home", href=url_for("index")))
            with div(id_="content"):
                content_func()


def counter_template(i, inc=1):
    h1("The counter is: ", i)
    with p():
        label("Increment with:")
        inc_with = input_(type_="number", value=inc)
    with p():
        input_(
            type_="button", onclick=(increase_counter, inc_with), value="Add")


@callback_route(app, '/inc/')
def increase_counter(inc):
    global i
    i += inc
    return hypergen(counter_template, i, inc, target_id="content")


@app.route('/counter/')
def counter():
    return hypergen(base_template, partial(counter_template, i))


INPUT_TYPES = [
    "button", "checkbox", "color", "date", "datetime", "datetime-local",
    "email", "file", "hidden", "image", "month", "number", "password", "radio",
    "range", "reset", "search", "submit", "tel", "text", "time", "url", "week"
]

SUB_ID = "inp-type-"


@callback_route(app, '/submit-inputs/')
def submit_inputs(value, type_):
    def template():
        with pre(style={"padding": 0}):
            raw(repr(value), " (", type(value).__name__, ")")

    return hypergen(template, target_id=SUB_ID + type_)


@app.route('/inputs/')
def inputs():
    def template():
        h1("Showing all input types.")
        with table():
            tr(th.r("Input type"), th.r("Element"), th.r("Server value"))

            for type_ in INPUT_TYPES:
                with tr():
                    cb = (submit_inputs, THIS, type_)
                    attrs = dict(onclick=cb, oninput=cb)
                    if type_ in ["button", "image", "reset", "submit"]:
                        attrs["value"] = "Click"
                    td(type_)
                    with td():
                        input_(type_=type_, **attrs)
                    td("", id_=SUB_ID + type_)

    return hypergen(base_template, partial(template))


@app.route('/')
def index():
    def template():
        h1("Browse the following examples")
        ul(
            li.r(a.r("Basic counter", href=url_for("counter"))),
            li.r(a.r("Input fields", href=url_for("inputs"))), )

    return hypergen(base_template, template)
