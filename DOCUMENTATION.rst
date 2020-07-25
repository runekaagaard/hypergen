Client / Server Communication Format
====================================

Server -> Client
----------------

The client can receive a list of commands, must of whom manipulates the DOM. This happens automatically in the liveview life cycle, but commands can be executed manually by the following javascript::

    import { execute_commands } from 'hypergen'

    execute_commands([
        ["hypergen.morph", {}, "id-of-element", "<div>New html for this section</div>"],
        ["hypergen.flash", {sticky: true}, "Updated the page!"],
    ])

or if building javascript is not your thing::

    window.hypergen.execute_commands([
        ["hypergen.morph", {}, "id-of-element", "<div>New html for this section</div>"],
        ["hypergen.flash", {sticky: true}, "Updated the page!"],
    ])

Each command is an array on the form `[NAME, KEYWORD_ARGUMENTS, ARG1, ARG2, ..., ARGN]`.
