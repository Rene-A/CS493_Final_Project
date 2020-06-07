from flask import Blueprint, request, make_response
from google.cloud import datastore
from json2html import *
import json
import constants
import helper
import verify_helper

client = datastore.Client()

bp = Blueprint('library', __name__, url_prefix='/libraries')

# The bits of code on making responses comes straight from the lectures on advanced api


@bp.route('', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def libraries_get_post():

    if request.method not in ["GET", "POST"]:

        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", ["GET", "POST"])
        return res

    # Test that the user is requesting JSON and that the user is registered with our application.
    if helper.is_requesting_json(request) is False:
        return {"Error": constants.error_406_json}, 406

    sub = verify_helper.get_sub(request)

    if sub is None or helper.sub_matches_user(client, sub) is False:
        return {"Error": constants.error_401_bad_jwt}, 401

    if request.method == 'POST':

        library, status = helper.create_library(client, request, sub)
        return json.dumps(library), status

    elif request.method == 'GET':

        # Now have to add pagination
        # { next: link to next page,
        #   count: 3,
        #   libraries: [{lib1}, {lib2}, {lib3}] }
        libraries, status = helper.get_library_page(client, request, sub)
        return json.dumps(libraries), status


@bp.route('/<id>', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def libraries_get_put_patch_delete(id):

    if request.method in ["GET", "PUT", "PATCH"]:

        # Test that the user is requesting JSON and that the user is registered with our application.
        if helper.is_requesting_json(request) is False:
            return {"Error": constants.error_406_json}, 406

        sub = verify_helper.get_sub(request)

        if sub is None or helper.sub_matches_user(client, sub) is False:
            return {"Error": constants.error_401_bad_jwt}, 401

        if request.method == 'GET':

            library, status = helper.get_library_with_status(client, request, id, sub)

            return json.dumps(library), status

        elif request.method == 'PUT':

            library, status = helper.put_library(client, request, id, sub)

            return json.dumps(library), status

        elif request.method == 'PATCH':

            library, status = helper.patch_library(client, request, id, sub)

            return json.dumps(library), status

    elif request.method == 'DELETE':

        sub = verify_helper.get_sub(request)

        if sub is None or helper.sub_matches_user(client, sub) is False:
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


@bp.route('/<library_id>/books/<book_id>', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def libraries_books_put_delete(library_id, book_id):

    if request.method not in ["PUT", "DELETE"]:

        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", ["PUT", "DELETE"])
        return res

    sub = verify_helper.get_sub(request)

    if sub is None or helper.sub_matches_user(client, sub) is False:
        return {"Error": constants.error_401_bad_jwt}, 401

    if request.method == 'PUT':

        message, status = helper.put_book_in_library(client, request, library_id, book_id, sub)

        return json.dumps(message), status

    elif request.method == 'DELETE':

        message, status = helper.remove_book_from_library(client, request, library_id, book_id, sub)

        return json.dumps(message), status
