# Local Variables:
# flymake-mode: nil
# End:
# yapf: disable

from hypergen import hypergen, dom, State


def login_form(state):
    def submit(request, state):
        if request.user.logged_in:
            auth.logout(request.user)

        is_ok = auth.login(state.email, state.password)
        if is_ok:
            dom.redirect("/dashboard/")
        else:
            state.errors.append("Invalid email or password")

    def errors(errors):
        with ul(when=errors, _class="errors"):
            [li(x) for x in errors]

    with form_cm(validators=[validators.no_duplicate_values],
                 onchange=validators.validate):
        errors(state.errors)

        label("Email")
        errors(state.email.errors)
        input_(value=state.email, type_="email", validators=[
            validators.no_gmail_account])

        label("Password")
        errors(state.password.errors)
        input_(value=state.password, type_="password", required=True)

        button("Login", onclick=submit)

@path("/auth/login/")
def login(request):
    state = State(errors=[], password="1234")
    return Response(hypergen(login_form, state))
