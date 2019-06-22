# coding=utf-8
from __future__ import (absolute_import, division, unicode_literals)
# yapf: disable
# To run, pip install flask, and then
#     FLASK_ENV=development FLASK_APP=flask_example flask run

from functools import partial

from flask import Flask, url_for
from hypergen import (flask_liveview_hypergen as hypergen,
                      flask_liveview_callback_route as callback_route, div,
                      input_, script, raw, label, p, h1, ul, li, a, html, head,
                      body, link, table, tr, th, td, THIS, pre, section, ol,
                      write, span, button, b, skippable, fieldset, legend,
                      style, form, select, option)
from random import randint
from itertools import takewhile

NORMALISE = "https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css"
SAKURA = "https://unpkg.com/sakura.css/css/sakura.css"
JQUERY = "https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js"
MORPHDOM = "https://cdn.jsdelivr.net/npm/morphdom@2.5.4/dist/morphdom.min.js"

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
            script("module = {}")
            script(src=MORPHDOM)
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
            li.r(a.r("Petals around the rose", href=url_for("petals"))),
            li.r(a.r("A basic form", href=url_for("a_basic_form"))),
        )

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
RULES = (
    ("The name of the game is Petals Around the Rose, and the name of the "
     "game is the key to the game."),
    "The answer is always zero or an even number.",
    ("Anyone who knows the game may give the answer to any roll, but they "
     "must not disclose the reasoning."))
DESCRIPTION = section.r(
    p.r("There are three rules:", ol.r(li.r(x) for x in RULES)),
    p.r("Get six correct answers in a row to become a Potentate of the Rose."))
QUESTIONS = []
ANSWERS = []

def petals_template():
    def dies(question, font_size="50px"):
        return span.r(
            (DIES[x - 1] for x in question),
            sep=" ",
            style={"font-size": font_size})

    def facit(question):
        return sum(PETALS.get(x, 0) for x in question)

    streak = len(list(takewhile(lambda x: facit(x[0]) == x[1],
                                zip(QUESTIONS[1:], ANSWERS[1:]))))

    write(DESCRIPTION)
    if streak > 5:
        p(b.r("Congrats! You are now a Potentate of the Rose. Hush."))

    p(dies(QUESTIONS[0]))

    with p.c():
        label("Whats the answer?")
        answer = input_(type_="number", name="answer")
        input_(type="button", value="Submit", onclick=(petal_answer, answer))
        span("Streak: ", streak, sep=" ", style="margin-left: 8px")

    if ANSWERS:
        with table.c():
            tr(th.r(x) for x in ("Throw", "Your answer", "Correct answer"))
            for question, answer in zip(QUESTIONS[1:], ANSWERS[1:]):
                tr(td.r(x) for x in (dies(question, "30px"), answer,
                                     facit(question)))


def roll():
    QUESTIONS.insert(0, [randint(1, 6) for _ in range(5)])
    ANSWERS.insert(0, None)
roll()

@callback_route(app, '/petal-answer/')
def petal_answer(answer):
    if answer is None:
        return None
    ANSWERS[0] = answer
    roll()
    return hypergen(petals_template, target_id="content")


@app.route('/petals/')
def petals():
    return hypergen(base_template, petals_template)


### A basic form ###

GRID = ("")
CSS = """
form { display: grid;grid-template-columns: repeat(2,1fr);grid-column-gap: 10px;
    grid-row-gap: 10px; }
input { width: 90% }
"""
COLORS = ("Red", "Black", "Silver")
RED, BLACK, SILVER = range(len(COLORS))
class Db:
    i = 0
    @staticmethod
    def new_id():
        Db.i += 1
        return "veh{}".format(Db.i)

    @staticmethod
    def empty_row():
        return [Db.new_id(), "", "", ""]

Db.vehicles = [
    [Db.new_id(), "Bugatti Chiron Sport", 261, RED],
    [Db.new_id(), "Mercedes-AMG Project One", 261, SILVER],
    [Db.new_id(), "Lamborghini Aventador SVJ", 217, BLACK],
]

@callback_route(app, '/add-vehicle/')
def add_vehicle(vehicles):
    Db.vehicles = vehicles
    Db.vehicles.append(Db.empty_row())

    return hypergen(a_basic_form_template, target_id="content")

@callback_route(app, '/remove-vehicle/')
def remove_vehicle(id_, vehicles):
    Db.vehicles = [x for x in vehicles if x[0] != id_]

    return hypergen(a_basic_form_template, target_id="content")

@callback_route(app, '/save/')
def save(vehicles):
    Db.vehicles = vehicles
    return hypergen(a_basic_form_template, target_id="content")


def a_basic_form_template():
    style(CSS)
    with fieldset.c(legend.r("Garage")):
        with form.c():
            div(label.r("Name"), input_.r())
            div(label.r("Address"), input_.r())
            div(label.r("Number of employees"), input_.r(type_="number"))

    fields = []
    with fieldset.c(legend.r("Vehicles")):
        with table.c(tr.r(th.r(x) for x in ("Model", "MPH", "Color", ""))):
            for id_, model, mph, color in Db.vehicles:
                row = [id_]
                tr(
                    td.r(input_.r(value=model, add_to=row)),
                    td.r(input_.r(value=mph, type_="number", add_to=row)),
                    td.r(select.r(option.r("-----"),
                        (option.r(x, value=j, selected=j==color)
                         for j, x in enumerate(COLORS))), add_to=row),
                    td.r(input_.r(type_="button", value="X", onclick=(
                        remove_vehicle, id_, fields), lazy=True))
                )
                fields.append(row)

        input_(type_="button", value="+", style={"width": "50px"},
               onclick=[add_vehicle, fields])

    with div.c():
        input_(type_="button", value="Save", onclick=(save, fields), lazy=True)

@app.route('/a-basic-form/')
def a_basic_form():
    return hypergen(base_template, a_basic_form_template)
