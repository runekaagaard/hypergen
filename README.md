# Welcome to hypergen
Pure python, threadsafe, parallizable, caching and diffing html generator. No more templates, just write python (or cython). Includes a liveview feature similar to Phoenix Liveview.

# How to try the demos?

```bash
git clone git@github.com:runekaagaard/hypergen.git
cd hypergen/src/
virtualenv venv
source venv/bin/activate
pip install Werkzeug==0.16.1 flask==1.1.1
FLASK_ENV=development FLASK_APP=flask_example flask run
```

Then browse to http://127.0.0.1:5000. The src for the demos can be found at https://github.com/runekaagaard/hypergen/blob/master/src/flask_example.py.

# Example todo app in flask:

```python
from hypergen import *
from flask import Flask

app = Flask(__name__)

# Automatically setup flask routes for callbacks.
flask_liveview_autoroute_callbacks(app, "/cbs/")

# This is our base template, that can be shared between pages.
def base_template(content_func):
    doctype()
    with html.c():
        with head.c():
            title("I 3> hypergen")
            script(src="hypergen.js")

        with body.c():
            with div.c(id_="content"):
                content_func()

# Below is the todo app.
                
TODOS = {
    "items": [
        {"task": "Remember the milk", "is_done": False},
        {"task": "Walk the dog", "is_done": False},
        {"task": "Get the kids to school", "is_done": True},
    ],
    "toggle_all": False,
    "filt": None,
}

def todomvc_toggle_all(is_done):
    TODOS["toggle_all"] = is_done

    for item in TODOS["items"]:
        item["is_done"] = is_done

def todomvc_toggle_one(i, is_done):
    TODOS["items"][i]["is_done"] = is_done

def todomvc_add(task):
    TODOS["items"].append({"task": task, "is_done": False})

def todomvc_clear_completed():
    TODOS["items"] = [x for x in TODOS["items"] if not x["is_done"]]

def todomvc_set_filter(filt):
    TODOS["filt"] = filt

def todomvc_template():
    style("input{margin-right: 6px;} ul{list-style: none; padding-left: 0;}")
    input_(type_="checkbox", checked=TODOS["toggle_all"], onclick=(todomvc_toggle_all, THIS))
    new_item = input_(placeholder="What needs to be done?")
    input_(type_="button", value="Add", onclick=(todomvc_add, new_item))
    with ul.c():
        for i, item in enumerate(TODOS["items"]):
            if TODOS["filt"] is not None and TODOS["filt"] != item["is_done"]:
                continue
            with li.c():
                input_(type_="checkbox", checked=item["is_done"],
                       onclick=(todomvc_toggle_one, i, THIS))
                write(item["task"])
                
    input_(type_="button", value="All", onclick=(todomvc_set_filter, None))
    input_(type_="button", value="Active", onclick=(todomvc_set_filter, False))
    input_(type_="button", value="Completed", onclick=(todomvc_set_filter, True))
    input_(type_="button", value="Clear completed", onclick=(todomvc_clear_completed, ))

@app.route('/todomvc/')
def todomvc():
    def callback_output():
        return hypergen(todomvc_template, target_id="content", flask_app=app)

    html = hypergen(base_template, todomvc_template, flask_app=app,
                    callback_output=callback_output)

    return html
```
