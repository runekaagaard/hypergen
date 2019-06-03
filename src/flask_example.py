# To run, pip install flask, and then
#     FLASK_ENV=development FLASK_APP=flask_example flask run

from functools import partial

from flask import Flask, url_for
from hypergen import (flask_liveview_hypergen as hypergen,
                      flask_liveview_callback_route as callback_route, div,
                      input_, script, raw, label, p, h1, ul, li, a, html, head,
                      body, link)

app = Flask(__name__)

i = 0


@callback_route(app, '/inc/')
def increase_counter(inc):
    global i
    i += inc
    return hypergen(counter_template, i, inc, target_id="main")


def base_template(content_func):
    raw("<!DOCTYPE html>")
    with html():
        with head():
            link(
                href=
                "https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css",
                rel="stylesheet",
                type_="text/css")
            link(
                href="https://unpkg.com/sakura.css/css/sakura.css",
                rel="stylesheet",
                type_="text/css")
            script(
                src=
                "https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"
            )
            with script(), open("hypergen.js") as f:
                raw(f.read())

        with body():
            div(a.r("Home", href=url_for("index")))
            with div(id_="main"):
                content_func()


def counter_template(i, inc=1):
    h1("The counter is: ", i)
    with p():
        label("Increment with:")
        inc_with = input_(type_="number", value=inc)
    with p():
        input_(
            type_="button", onclick=(increase_counter, inc_with), value="Add")


def index_template():
    h1("Browse the following examples")
    ul(li.r(a.r("Basic counter", href=url_for("counter"))))


@app.route('/counter/')
def counter():
    return hypergen(base_template, partial(counter_template, i))


@app.route('/')
def index():
    return hypergen(base_template, index_template)
