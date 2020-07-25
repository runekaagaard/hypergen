Client Communication Format
===========================

Every time a client side event (onchange, onclick, etc.) triggers a callback view function on the server, the server returns a list of commands for the client to execute. Most of whom manipulates the DOM.

On the server this looks like this:

.. code-block:: python
                
    from hypergen import LiveviewResponse, command as cmd
    
    @permission_required("myapp.myperm")
    def my_callback(request):
        return LiveviewResponse([
            cmd("hypergen.morph", "id-of-element", "<div>New html for this section</div>"),
            cmd("hypergen.flash", "Updated the page!", sticky=True),
        ])

This generates json that can be read by the client:
     
.. code-block:: javascript

    {
        "status": 200,
        "commands": [
            ["hypergen.morph", "id-of-element", "<div>New html for this section</div>", {}],
            ["hypergen.flash", "Updated the page!", {sticky: true}],
        ]
    }

Thus it is completely possible to use different frameworks and languages in the backend.
        
Commands can be executed manually on the client as well:

.. code-block:: javascript
                
    import { execute_commands } from 'hypergen'

    execute_commands([
        ["hypergen.morph", "id-of-element", "<div>New html for this section</div>", {}],
        ["hypergen.flash", "Updated the page!", {sticky: true}],
    ])

Each command is an array on the form ``[NAME, ARG1, ARG2, ..., ARGN, KEYWORD_ARGUMENTS]``, where:

*NAME*
    The name of a command function in ``hypergen.commands``. Add your own custom commands to
    ``hypergen.commands``.
*ARG1, ARG2, ..., ARGN*
    Optional positional keyword arguments to the command function.
*KEYWORD_ARGUMENTS*
    A required object with optional keyword arguments. Will be given as the last argument to the
    command function.

Supported Client Commands
=========================

hypergen.morph(id_of_element, new_html)
---------------------------------------

Updates the given element with new html. Uses morphdom for efficency.

hypergen.delete(id_of_element)
------------------------------

Deletes given element.

hypergen.flash(message, sticky=False)
--------------------------------

Display a notification message. Set ``sticky`` to true to persist the message.

hypergen.focus(id_of_element)
------------------------------

Changes the focus to the given element.

hypergen.blur()
---------------

Removes the focus from the focused element, if any.

hypergen.block(execution_groups)
--------------------------------

Blocks execution of events for the given execution groups. Use ``"*"`` to block all execution groups.

hypergen.release(execution_groups)
--------------------------------

Resumes execution of events for the given execution groups. Use ``"*"`` to resume all execution groups.

hypergen.set_state(path, data, merge=False)
-------------------------------------------

Set or merges the client state at the given path.

hypergen.switch_mode(mode_name)
-------------------------------

Changes to another execution mode. Hypergen supports out of the box: "MAIN", "OFFLINE" and "SERVER_ERROR_500".
