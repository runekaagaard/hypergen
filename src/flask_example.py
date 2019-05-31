from flask import Flask, request, jsonify
from hypergen import hypergen, div, input_, script, raw

app = Flask(__name__)

i = 0


@app.route('/inc/', methods=['POST'])
def increase_counter():
    global i
    args = request.get_json()
    print "ARGS IT", args
    inc, = args
    i += int(inc)
    print "NEW I IS", i
    return jsonify(
        hypergen(
            hello_counter_template,
            i,
            int(inc),
            liveview=True,
            auto_id=True,
            target_id="counter"))


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


def hello_counter_template(i, inc=1):
    with div():
        div("Increment with:")
        inc_with = input_(type_="number", value=inc)
        div("The counter is: ", i)
        input_(
            type_="button", onclick=(increase_counter, inc_with), value="More")


@app.route('/')
def hello_counter():
    return hypergen(
        base_template, hello_counter_template, i, auto_id=True,
        liveview=True)[0][-1]
