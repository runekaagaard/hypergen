# coding=utf-8
from __future__ import (absolute_import, division, unicode_literals)
# To run, pip install flask, and then
#     FLASK_ENV=development FLASK_APP=flask_example flask run

from functools import partial

from flask import Flask, url_for
from hypergen import (flask_liveview_hypergen as hypergen,
                      flask_liveview_callback_route as callback_route, div,
                      input_, script, raw, label, p, h1, ul, li, a, html, head,
                      body, link, table, tr, th, td, THIS, pre, section, ol,
                      write, span, button)
from random import randint

NORMALISE = "https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css"
SAKURA = "https://unpkg.com/sakura.css/css/sakura.css"
JQUERY = "https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"

app = Flask(__name__)
i = 0

### Shared base ###


def base_template(content_func):
    raw("<!DOCTYPE html>")
    with html.c():
        with head.c():
            link(href=NORMALISE, rel="stylesheet", type_="text/css")
            link(href=SAKURA, rel="stylesheet", type_="text/css")
            script(src=JQUERY)
            with script.c(), open("hypergen.js") as f:
                raw(f.read())

        with body.c():
            div(a.r("Home", href=url_for("index")))
            with div.c(id_="content"):
                content_func()


### Home ###


@app.route('/')
def index():
    def template():
        h1("Browse the following examples")
        ul(
            li.r(a.r("Basic counter", href=url_for("counter"))),
            li.r(a.r("Input fields", href=url_for("inputs"))),
            li.r(a.r("Petals around the rose", href=url_for("petals"))), )

    return hypergen(base_template, template)


### Counter ###


def counter_template(i, inc=1):
    h1("The counter is: ", i)
    with p.c():
        label("Increment with:")
        inc_with = input_(type_="number", value=inc)
    with p.c():
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


### Inputs ###

INPUT_TYPES = [
    "button", "checkbox", "color", "date", "datetime", "datetime-local",
    "email", "file", "hidden", "image", "month", "number", "password", "radio",
    "range", "reset", "search", "submit", "tel", "text", "time", "url", "week"
]

SUB_ID = "inp-type-"


@callback_route(app, '/submit-inputs/')
def submit_inputs(value, type_):
    def template():
        with pre.c(style={"padding": 0}):
            raw(repr(value), " (", type(value).__name__, ")")

    return hypergen(template, target_id=SUB_ID + type_)


@app.route('/inputs/')
def inputs():
    def template():
        h1("Showing all input types.")
        with table.c():
            tr(th.r(x) for x in ["Input type", "Element", "Server value"])

            for type_ in INPUT_TYPES:
                cb = (submit_inputs, THIS, type_)
                attrs = dict(onclick=cb, oninput=cb)
                if type_ in ["button", "image", "reset", "submit"]:
                    attrs["value"] = "Click"
                tr(td.r(type_),
                   td.r(input_.r(type_=type_, **attrs)),
                   td.r(id_=SUB_ID + type_))

    return hypergen(base_template, template)


### Petals around the rose ###
PETALS = {3: 2, 5: 4}
DIES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
R1 = ("The name of the game is Petals Around the Rose, and the name of the "
      "game is the key to the game.")
R2 = "The answer is always zero or an even number."
R3 = ("Anyone who knows the game may give the answer to any roll, but they "
      "must not disclose the reasoning.")
RULES = section.r(
    p.r("There are three rules:", ol.r(li.r(x) for x in [R1, R2, R3])),
    p.r("Get six correct answers in a row to become a Potentate of the Rose."))
QUESTIONS = []
ANSWERS = []


def petals_template():
    write(RULES)

    def question_template(question, show_answer=True):
        p(
            span.r(
                (DIES[x - 1] for x in question),
                sep=" ",
                style={"font-size": "50px"}), )
        with p.c():
            label.r("Whats the answer?")
            answer = input_(type_="number")
            button("Submit", onclick=(petal_answer, answer))

    question_template(QUESTIONS[-1], False)
    with table.c():
        tr(th.r(x.capitalize()) for x in ("throw", "answer", "correct answer"))
        for question, answer in zip(reversed(QUESTIONS), reversed(ANSWERS)):
            tr(
                td.r(x)
                for x in ((DIES[x - 1]
                           for x in question), answer, result(question)))


def result(question):
    return sum(PETALS.get(x, 0) for x in question)


def roll():
    QUESTIONS.append([randint(1, 6) for _ in range(5)])


@callback_route(app, '/petal-answer/')
def petal_answer(answer):
    ANSWERS.append(answer)
    html = hypergen(base_template, petals_template, target_id="content")
    roll()
    return html


@app.route('/petals/')
def petals():
    roll()
    return hypergen(base_template, petals_template)
