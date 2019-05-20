def page(title, content):
    menu()
    with div_cm("outer"), div_cm("inner"):
        h1(title)
        content()
    footer()


@li(lambda item: item.title,
    signature=lambda f, item: [f, item.id, item.version])
def todo_item(item):
    pass


def index(reverse=False):
    p("Show last first" if reverse else "Show first first",
      onclick=(index, not reverse))

    todo_lists = db.todo_lists(reverse)
    for todo_list in todo_lists:
        h2(todo_list.title)
        with ul_cm():
            for item in todo_list.items:
                with li_cm(item.title):
                    span("complete", onclick=(complete, item.id))
                    span("edit", onclick=(complete, item.id))


print hypergen(page, partial(index))
