# To run, pip install flask, and then
#     FLASK_ENV=development FLASK_APP=flask_example flask run

from functools import partial

from flask import Flask
from hypergen import (flask_liveview_hypergen as hypergen,
                      flask_liveview_callback_route as callback_route, div,
                      input_, script, raw, label, p, h1)

app = Flask(__name__)

i = 0


@callback_route(app, '/inc/')
def increase_counter(inc):
    global i
    i += inc
    return hypergen(hello_counter_template, i, inc, target_id="counter")


def base_template(content_func):
    script(
        src="https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"
    )
    with script(), open("hypergen.js") as f:
        raw(f.read())
    with div(id_="counter"):
        content_func()


def hello_counter_template(i, inc=1):
    h1("The counter is: ", i)
    with p():
        label("Increment with:", style={"display": "block"})
        inc_with = input_(type_="number", value=inc)
    with p():
        input_(
            type_="button", onclick=(increase_counter, inc_with), value="Add")


@app.route('/')
def hello_counter():
    return hypergen(base_template, partial(hello_counter_template, i))
