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
        



This happens automatically in the liveview life cycle, but commands can be executed manually by the following javascript:

.. code-block:: javascript
    import { execute_commands } from 'hypergen'

    execute_commands([
        ["hypergen.morph", {}, "id-of-element", "<div>New html for this section</div>"],
        ["hypergen.flash", {sticky: true}, "Updated the page!"],
    ])

or if building javascript is not your thing:

.. code-block:: javascript
                
    window.hypergen.execute_commands([
        ["hypergen.morph", {}, "id-of-element", "<div>New html for this section</div>"],
        ["hypergen.flash", {sticky: true}, "Updated the page!"],
    ])

Each command is an array on the form ``[NAME, KEYWORD_ARGUMENTS, ARG1, ARG2, ..., ARGN]``, where:

*NAME*
    The name of a command function in ``hypergen.commands``. Add your own custom commands to
    ``hypergen.commands``.
*KEYWORD_ARGUMENTS*
    An object with optional keyword arguments. Will be given as the first argument to the command
    function.
*ARG1, ARG2, ..., ARGN*
    Optional positional keyword arguments to the command function.
