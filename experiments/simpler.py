from framework import path, perm, db
from hypergen import hypergen, scope
from hypergen.elements import ul, li, span, input_, button, h2


@hypergen
@perm("todos")
@path("todos")
def todos(request, errors=None):
    def update(item_id, scope):
        db.update_item(item_id, scope["title"], scope["description"])

    def mark_all(todo_list_id, is_done):
        db.mark_all(todo_list_id, is_done)

    def mark_one(item_id, is_done):
        db.mark_one(item_id, is_done)

    for todo_list in db.todo_lists(user=request.user):
        h2(todo_list.title)
        with scope("todo_list"), ul(class_="todos"):
            button(
                "Mark all completed", onclick=(mark_all, todo_list.id, True))

            for item in todo_list:
                with scope("item"), li():
                    span(item.title, name="title", contenteditable=True)
                    input_(name="description", value=item.description)
                    button("Update", onclick=("update", item.id, "*"))
