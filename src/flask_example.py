from functools import partial

from flask import Flask
from hypergen import hypergen, div, input_, script, raw

app = Flask(__name__)

i = 0


@hypergen(target_id="counter")
@app.route('/inc/', methods=['POST'])
def increase_counter(inc):
    global i
    i += inc
    return hello_counter_template(i, inc)


@hypergen(as_deltas=False)
def base_template(content_func, *args, **kwargs):
    script(
        None,
        integrity="sha256-ZosEbRLbNQzLpnKIkEdrPv7lOy9C27hHQ+Xp8a4MxAQ=",
        crossorigin="anonymous",
        src="https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"
    )
    with script(), open("hypergen.js") as f:
        raw(f.read())
    with div(id_="counter"):
        content_func(*args, **kwargs)


def hello_counter_template(i, inc=1):
    with div():
        div("Increment with:")
        inc_with = input_(type_="number", value=inc)
        div("The counter is: ", i)
        input_(
            type_="button", onclick=(increase_counter, inc_with), value="More")


@app.route('/')
def hello_counter():
    return base_template(partial(hello_counter_template, i))
