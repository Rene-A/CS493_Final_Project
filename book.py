from flask import Blueprint, request, make_response
from google.cloud import datastore
from json2html import *
import json
import constants
import helper
import verify_helper

client = datastore.Client()

bp = Blueprint('book', __name__, url_prefix='/books')

# The bits of code on making responses comes straight from the lectures on advanced api


@bp.route('', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def books_get_post():
    if request.method == 'POST':

        sub = verify_helper.get_sub(request)

        if sub is None:
            return {"Error": constants.error_401_bad_jwt}, 401

        boat, status = helper.create_library(client, request, sub)
        return json.dumps(boat), status

    elif request.method == 'GET':

        boats, status = helper.get_entity_list(client, constants.libraries)
        return json.dumps(boats), status

    else:

        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", ["GET", "POST"])
        return res


@bp.route('/<id>', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def books_get_put_patch_delete(id):

    if request.method == 'DELETE':

        sub = verify_helper.get_sub(request)

        if sub is None:
            return {"Error": constants.error_401_bad_jwt}, 401

        payload, status = helper.delete_library(client, id, sub)

        if status != 204:

            return json.dumps(payload), status

        return ('', 204)

    else:
        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", ["GET", "PUT", "PATCH", "DELETE"])
        return res
