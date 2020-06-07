# Started this code off the files we were allowed to use.
from google.cloud import datastore
from flask import Flask, request, url_for, render_template
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

import library
import random
import helper
import verify_helper
import config
import user
import book

# This disables the requirement to use HTTPS so that you can test locally.
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.register_blueprint(library.bp)
app.register_blueprint(user.bp)
app.register_blueprint(book.bp)

client = datastore.Client()

# These should be copied from an OAuth2 Credential section at
# https://console.cloud.google.com/apis/credentials
client_id = config.client_id
client_secret = config.client_secret

# This is the page that you will use to decode and collect the info from
# the Google authentication flow
redirect_uri = config.redirect_uri

random.seed()

# These let us get basic info to identify a user and not much else
# they are part of the Google People API
scope = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'openid']
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

# This link will redirect users to begin the OAuth flow with Google
@app.route('/')
def index():

    state = "SimpleSecret" + str(random.randint(10000, 100000000))

    while True:

        if not verify_helper.state_exists(client, state):
            break

        state = "SimpleSecret" + str(random.randint(10000, 100000000))

    verify_helper.store_state(client, state)

    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline", prompt="select_account", state=state)

    return render_template("welcome.html", google_url=authorization_url)


# This is where users will be redirected back to and where you can collect
# the JWT for use in future requests
@app.route('/oauth')
def oauthroute():
    state = request.args["state"]
    print(state)

    if not verify_helper.state_exists(client, state):
        return {"Error": "The state returned was incorrect."}, 400

    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=client_secret)
    req = requests.Request()

    id_info = id_token.verify_oauth2_token(token['id_token'], req, client_id)

    # https://google-auth.readthedocs.io/en/latest/reference/google.oauth2.id_token.html
    # Straight from the documentation for this function.
    if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:

        return {"Error": "The JWT is invalid.  The issuer is listed as: " + id_info["iss"]}, 400

    # Need to create the user account and store the sub value of their jwt as the user's unique_id.
    # Skip account creation if the user already has an account.  We only need to display their information again.
    if not helper.sub_matches_user(client, id_info["sub"]):

        payload = {"unique_id": id_info["sub"],
                   "email": id_info["email"]}
        # helper.create_user(client, request, {"unique_id": id_info["sub"]})
        helper.create_user(client, request, payload)

    verify_helper.delete_state(client, state)

    return render_template("user_info.html", token=token['id_token'], sub=id_info['sub'])


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
