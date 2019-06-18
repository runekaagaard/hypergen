Callback = namedtuple("Callback", "args debunce")


def callback(path, args=None, debounce=100):
    return Callback(path, args if args is not None else [], debounde)


def input_(**attrs):
    if state.auto_id is True and "id_" not in attrs:
        attrs["id_"] = next(state.iterid)
    if state.liveview is True:
        for k, v in attrs.iteritems():
            if k.startswith("on") and type(v) in (list, tuple, Callback):
                cb = callback(v[0], v[1:]) if type(v) in (list, tuple) else v
