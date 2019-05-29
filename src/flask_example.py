from flask import Flask, request
from hypergen import hypergen, div, input_, script, raw, div_o, div_c

app = Flask(__name__)

i = 0


@app.route('/inc/', methods=['POST'])
def increase_counter():
    print request
    global i
    i += 1
    return hypergen(hello_counter_template, i, True, liveview=True)


increase_counter.hypergen_url = '/inc/'


def hello_counter_template(i, partial=False):
    if not partial:
        raw("<!doctype html><html>")
        script(
            " ",
            integrity="sha256-ZosEbRLbNQzLpnKIkEdrPv7lOy9C27hHQ+Xp8a4MxAQ=",
            crossorigin="anonymous",
            src=
            "https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"
        )

        with script():
            with open("hypergen.js") as f:
                raw(f.read())
        div_o(id_="counter")

    with div():
        div("The counter is: ", i)
        input_(type="button", onclick=(increase_counter, 1), value="Moar")

    if not partial:
        div_c()
        raw("</html>")


@app.route('/')
def hello_counter():
    return hypergen(hello_counter_template, i, liveview=True)
