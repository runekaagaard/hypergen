from framework import path, perm, db
from hypergen import scope
from hypergen.elements import ul, li, span, input_, button, h2


# In hypergen.
def hypergen(func, *args, **kwargs):
    get_callback = kwargs.pop("get_callback")
    if get_callback is not None:
        callback = get_callback(func, *args, **kwargs)
        if callback is not None:
            response = callback()
            if response is not None:
                return response

    func(*args, **kwargs)

    return  # the html.


# In app.


def get_callback(func, request, *args, **kwargs):
    if not request.method == "POST" and request.is_xhr():
        return None
    else:
        """
        E.g. ["todos.views.todos|update", 91, {"title": "Milk",
            "description": "Just buy it!"}]
        """
        return request.POST.get("hypergen_callback")


@hypergen(get_callback=get_callback, dom_id="todos")
@perm("todos")
@path("todos")
def todos(request, errors=None):
    def update(item_id, values):
        db.update_item(item_id, values["title"], values["description"])

    def mark_all(todo_list_id, is_done):
        db.mark_all(todo_list_id, is_done)

    def mark_one(item_id, is_done):
        db.mark_one(item_id, is_done)

    for todo_list in db.todo_lists(user=request.user):
        h2(todo_list.title)
        with ul(class_="todos", scope="todo_list"):
            button(
                "Mark all completed", onclick=(mark_all, todo_list.id, True))

            for item in todo_list:
                with li(scope="item") as li_el:
                    span(item.title, name="title", contenteditable=True)
                    input_(name="description", value=item.description)

                    # Different examples of a server callback.
                    # The refs are referencing the dom value of the elements,
                    # not the elements themselves.

                    # With all data in scope.
                    button("Update", onclick=(update, item.id, "REF:*"))
                    # ... or with specific fields in scope.
                    button(
                        "Update",
                        onclick=(update, item.id, "REF:title,description"))
                    # ... or with all data in parent scope
                    button("Update", onclick=(update, item.id, "REF:.*"))
                    # ... or with everything.
                    button("Update", onclick=(update, item.id, "REF:ROOT"))

                    # ... or using ref string from return value of elements.
                    title = span(
                        item.title, name="title", contenteditable=True)
                    description = input_(
                        name="description", value=item.description)
                    button(
                        "Update",
                        onclick=(update, item.id, title.ref, description.ref))

                    # ... or using ref returned from scoped context manager
                    # element.
                    button("Update", onclick=(update, item.id, li_el.ref))
