from flask import Blueprint, session, request, redirect
from server.env import Env
from server.oauth import oauth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route('/login')
def login():
    if "redirect" in request.args:
        session["redirect"] = request.args["redirect"]
    return oauth.auth.authorize_redirect(Env.get("PUBLIC_URL") + "/auth/callback")


@auth_bp.route('/callback')
def callback():
    token = oauth.auth.authorize_access_token()
    user = oauth.auth.parse_id_token(token)

    if not user:
        return "failed to authenticate", 500

    session['user'] = user
    session.permanent = True

    return redirect(session.pop('redirect')) if "redirect" in session else redirect("/")


@auth_bp.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(Env.get('OAUTH_LOGOUT_URL') + "?redirect=" + (
        request.args['redirect'] if "redirect" in request.args.keys() else Env.get("PUBLIC_URL")
    ))
