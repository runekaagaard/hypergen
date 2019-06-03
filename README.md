# python-htmlgen
Pure python, threadsafe, parallizable, caching and diffing html generator. No more templates, just write python (or cython). Includes a liveview feature similar to Phoenix Liveview.

# Example of liveview features inside a flask app.

```python
# To run, pip install flask, and then
#     FLASK_ENV=development FLASK_APP=flask_example flask run

from functools import partial

from flask import Flask, url_for
from hypergen import (flask_liveview_hypergen as hypergen,
                      flask_liveview_callback_route as callback_route, div,
                      input_, script, raw, label, p, h1, ul, li, a, html, head,
                      body, link)

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


@app.route('/')
def index():
    def template():
        h1("Browse the following examples")
        ul(li.r(a.r("Basic counter", href=url_for("counter"))))

    return hypergen(base_template, template)

```
