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

    if request.method not in ["GET", "POST"]:

        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", ["GET", "POST"])
        return res

    # Test that the user is requesting JSON and that the user is registered with our application.
    if helper.is_requesting_json(request) is False:
        return {"Error": constants.error_406_json}, 406

    if request.method == 'POST':

        book, status = helper.create_book(client, request)
        return json.dumps(book), status

    elif request.method == 'GET':

        # Now have to add pagination
        # { next: link to next page
        #   count: 3
        #   books: [{book1}, {book2}, {book3}] }
        books, status = helper.get_book_page(client, request)
        return json.dumps(books), status


@bp.route('/<id>', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def books_get_put_patch_delete(id):

    if request.method in ["GET", "PUT", "PATCH"]:

        # Test that the user is requesting JSON and that the user is registered with our application.
        if helper.is_requesting_json(request) is False:
            return {"Error": constants.error_406_json}, 406

        if request.method == 'GET':

            book, status = helper.get_book_with_status(client, request, id)

            return json.dumps(book), status

        elif request.method == 'PUT':

            book, status = helper.put_book(client, request, id)

            return json.dumps(book), status

        elif request.method == 'PATCH':

            book, status = helper.patch_book(client, request, id)

            return json.dumps(book), status

    elif request.method == 'DELETE':

        payload, status = helper.delete_book(client, id)

        if status != 204:

            return json.dumps(payload), status

        return ('', 204)

    else:
        res = make_response(json.dumps({"Error": constants.error_405_bad_method}))
        res.mime_type = "application/json"
        res.status_code = 405
        res.headers.set("Allow", ["GET", "PUT", "PATCH", "DELETE"])
        return res
