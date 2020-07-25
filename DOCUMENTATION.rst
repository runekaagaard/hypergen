Client / Server Communication Format
====================================

Server -> Client
----------------

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
    A required object with optional keyword arguments. Will be given as the first argument to the
    command function.
