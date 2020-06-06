from flask import Blueprint, request, make_response
from google.cloud import datastore
from json2html import *
import json
import constants
import helper
import verify_helper

client = datastore.Client()

bp = Blueprint('user', __name__, url_prefix='/users')

# The bits of code on making responses comes straight from the lectures on advanced api

@bp.route('', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def owner_get(owner_id):
    if request.method == 'GET':

        sub = verify_helper.get_sub(request)

        if sub is None:

            return {"Error": constants.error_401_bad_jwt}, 401

        boats, status = helper.get_owner_library_list(client, sub)
        return json.dumps(boats), status

    else:

        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", "GET")
        return res
