#!/usr/bin/env python3
"""
mcjapi service authentication with the Hub
"""
from functools import wraps
from datetime import datetime
import logging
import os
import re
import secrets
import sys

from flask import Flask, jsonify, make_response, redirect, request, session
from jupyterhub.services.auth import HubOAuth
from waitress import serve

from log_collect import log2db

prefix = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')
auth = HubOAuth(api_token=os.environ['JUPYTERHUB_API_TOKEN'], cache_max_age=60)
app = Flask(__name__)
# encryption key for session cookies
app.secret_key = secrets.token_bytes(32)

logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO, format="%(asctime)s %(message)s",
                    datefmt="%Y-%m-%y %H:%M:%S")
logger = logging.getLogger(__name__)
auth_header_pat = re.compile(r'^(?:token|bearer)\s+([^\s]+)$', flags=re.IGNORECASE)


def page_authenticated(f):
    """Decorator for authenticating with the Hub via OAuth"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get("token")
        if token:
            user = auth.user_for_token(token)
        else:
            user = None
        if user:
            return f(user, *args, **kwargs)
        else:
            # redirect to login url on failed auth
            state = auth.generate_state(next_url=request.path)
            response = make_response(redirect(auth.login_url + f'&state={state}'))
            response.set_cookie(auth.state_cookie_name, state)
            return response

    return decorated


def authenticated(f):
    """Decorator for authenticating with the Hub via OAuth"""

    def get_auth_token():
        """Get the authorization token from Authorization header"""
        auth_header = request.headers.get('Authorization', '')
        match = auth_header_pat.match(auth_header)
        if not match:
            return None
        return match.group(1)

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_auth_token()
        if token is None:
            return "invalid_header: token not found", 401

        user = auth.user_for_token(token)
        return f(user, *args, **kwargs)

    return decorated


@app.route(prefix + "log_collect", methods=["POST"])
@authenticated
def log_collect(user):

    if user is None:
        return jsonify({"message": "invalid user"}), 401

    if 'groups' not in user or 'Instructor' not in user['groups']:
        return jsonify({"message": "permission dinied"}), 403

    req_data = request.get_json()
    course = req_data.get('course')
    dt_from = req_data.get('from')
    dt_to = req_data.get('to')
    opt = {}
    if dt_from is not None:
        opt['dt_from'] = datetime.fromisoformat(dt_from)
    if dt_to is not None:
        opt['dt_to'] = datetime.fromisoformat(dt_to)
    if course is None:
        return jsonify({"message": "invalid parameters: course is missing"}), 400
    try:
        db_path = log2db(course, user["name"], **opt)
    except FileNotFoundError as e:
        return jsonify({"message": f"directory not found: {os.path.join('~', str(e))}"}), 400

    res = dict()
    res['db_path'] = db_path
    res['dt_from'] = opt.get('dt_from')
    res['dt_to'] = opt.get('dt_to')
    return jsonify(res)


@app.route(prefix + 'oauth_callback')
def oauth_callback():
    code = request.args.get('code', None)
    if code is None:
        return "Forbidden", 403

    # validate state field
    arg_state = request.args.get('state', None)
    cookie_state = request.cookies.get(auth.state_cookie_name)
    if arg_state is None or arg_state != cookie_state:
        # state doesn't match
        return "Forbidden", 403

    token = auth.token_for_code(code)
    # store token in session cookie
    session["token"] = token
    next_url = auth.get_next_url(cookie_state) or prefix
    response = make_response(redirect(next_url))
    return response


if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=10101)
