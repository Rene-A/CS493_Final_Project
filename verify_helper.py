# Functions that are only used for oauth 2.0

from google.cloud import datastore
from flask import request
from google.oauth2 import id_token
from google.auth.transport import requests
import constants
import config


# Accepts the token we received from the client.  This function attempts to verify that the token is correct,
# if the token is not correct, then the ValueError exception is thrown.  The except block then returns none to
# my main function.  Otherwise, the token's sub value representing the user is returned.
def get_sub(request):

    req = requests.Request()

    token = get_token(request)

    if token is None:

        return None

    # https://developers.google.com/identity/sign-in/web/backend-auth
    try:
        id_info = id_token.verify_oauth2_token(token, req, config.client_id)

        # Straight from the documentation
        # https://developers.google.com/identity/sign-in/web/backend-auth
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:

            raise ValueError('Wrong issuer.')

        return id_info["sub"]

    except ValueError:

        # Invalid token
        return None


def get_token(request):

    auth_string = request.headers.get("authorization")

    if auth_string is not None:

        # https://www.w3schools.com/python/ref_string_split.asp
        my_list = auth_string.split(maxsplit=2)

        first = my_list[0]
        second = my_list[1]

        if first == "Bearer":

            return second

    return None


def store_state(ds_client, state):

    state_entity = datastore.entity.Entity(key=ds_client.key(constants.states))
    state_entity["value"] = state
    ds_client.put(state_entity)


def state_exists(ds_client, state_to_check):
    # https://googleapis.dev/python/datastore/latest/client.html#google.cloud.datastore.client.Client.query
    query = ds_client.query(kind=constants.states)
    query.add_filter("value", "=", state_to_check)
    results = list(query.fetch())

    if len(results) != 0:
        return True

    return False


def delete_state(ds_client, state):
    # https://googleapis.dev/python/datastore/latest/client.html#google.cloud.datastore.client.Client.query
    query = ds_client.query(kind=constants.states)
    query.add_filter("value", "=", state)
    results = list(query.fetch())

    # https://cloud.google.com/appengine/docs/standard/python/datastore/entities
    for entity in results:

        ds_client.delete(entity.key)