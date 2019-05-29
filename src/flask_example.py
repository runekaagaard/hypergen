from flask import Flask
from hypergen import hypergen, div, input_, script, raw

app = Flask(__name__)

i = 0


@app.route('/inc/', methods=['POST'])
def increase_counter():
    global i
    i += 1
    return hypergen(hello_counter_template, i, liveview=True)


increase_counter.hypergen_url = '/inc/'


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


def hello_counter_template(i):
    with div():
        div("The counter is: ", i)
        input_(type="button", onclick=(increase_counter, 1), value="Moar")


@app.route('/')
def hello_counter():
    return hypergen(base_template, hello_counter_template, i, liveview=True)
