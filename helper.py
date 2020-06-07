# Rene Arana
# 4/18/2020
# List of helper function to make my life easier.

from google.cloud import datastore
import constants


def fill_entity(content, listOfKeys):

    newInfo = {}

    for key in listOfKeys:

        newInfo[key] = content[key]

    return newInfo


# Returns true if the json content has all the keys expected.
# Returns false if a key is missing, or if an extra key is provided.
def has_all_keys(content, listOfKeysExpected):

    # Simple check.  If our lists are not the same size, then there is no way that we have the keys we need.
    if len(content.keys()) == len(listOfKeysExpected):

        # Discussion of all and any from a Piazza post https://piazza.com/class/k85yqshkkvf2b3?cid=69
        # made by Jason Moule
        # https://www.w3schools.com/python/python_dictionaries.asp
        return all([x in content.keys() for x in listOfKeysExpected])

    return False


# Creates a new entity of the type kindOfEntity.  Input MUST be validated before calling this function.
# No error checking performed.
# Returns the new entity as a json object along with a 201 created code on success.
# The returned json entity will also include the entity's id and self link.
def create_entity(dsClient, request, content, keysExpected, kindOfEntity):

    new_entity = datastore.entity.Entity(key=dsClient.key(kindOfEntity))

    newInfo = fill_entity(content, keysExpected)

    new_entity.update(newInfo)
    dsClient.put(new_entity)

    new_entity["id"] = str(new_entity.key.id)
    new_entity["self"] = get_self(request, kindOfEntity, new_entity["id"])

    return new_entity, 201


# Creates a user entity.  Returns the new entity as a json object along with a 201 created code on success.
# The returned json entity will also include the entity's id and self link.
def create_user(dsClient, request, content):

    keysExpected = ["unique_id", "libraries"]

    content["libraries"] = []

    return create_entity(dsClient, request, content, keysExpected, constants.users)


# Creates a library entity.  Returns the new entity as a json object along with a 201 created code on success.
# The returned json entity will also include the entity's id and self link.
# { "id": 123,
#   "name": "Great Library",
#   "street_address": "123 Real Street",
#   "county": "Fairfax",
#   "state": "Virginia"
#   "librarian": <current_user>
#   "books": []
#   "self": <link>
# }
def create_library(dsClient, request, owner_sub):

    content = request.get_json()

    keysExpected = ["name", "street_address", "county", "state", "librarian", "books"]

    # The current user/librarian will be given ownership of this library.
    query = dsClient.query(kind=constants.users)
    query.add_filter("unique_id", "=", owner_sub)

    librarian = list(query.fetch())[0]

    content["librarian"] = {"id": librarian.key.id}
    content["books"] = []

    new_library, status = create_entity(dsClient, request, content, keysExpected, constants.libraries)

    new_library["librarian"]["self"] = get_self(request, constants.users, new_library["librarian"]["id"])

    librarian["libraries"].append({"id": new_library["id"]})
    dsClient.put(librarian)

    return new_library, status


# Creates a user entity.  Returns the new entity as a json object along with a 201 created code on success.
# The returned json entity will also include the entity's id and self link.
# { "id": 123,
#   "title": "Good Book",
#   "author": "Great Author",
#   "illustrator": "Good Artist",
#   "library": None
#   "self": <link>
# }
def create_book(dsClient, request):

    content = request.get_json()

    keysExpected = ["title", "author", "illustrator", "library"]

    if "illustrator" not in content.keys():

        content["illustrator"] = None

    content["library"] = None

    return create_entity(dsClient, request, content, keysExpected, constants.books)


# Returns the entity of type kindOfEntity with the provided id and self link.
# Returns status code 404 if the entity is not found.
# Otherwise, returns the Entity along with a status code.
def get_entity_with_info(dsClient, request, kindOfEntity, id):

    entity_key = dsClient.key(kindOfEntity, int(id))
    entity = dsClient.get(key=entity_key)

    # https://realpython.com/null-in-python/
    if entity is None:
        # We couldn't find an entity of that type with that id.
        return None, 404

    entity["id"] = str(entity.key.id)
    entity["self"] = get_self(request, kindOfEntity, entity["id"])
    return entity, 200


# Returns a library with the provided id and self link if everything works correctly.
# Returns an error message and 403 status if the library does not belong to the user.
# Returns an error message and 404 status if the entity is not found.
def get_library_with_status(dsClient, request, id, sub):

    library, status = get_entity_with_info(dsClient, request, constants.libraries, id)

    if status == 404:
        # We couldn't find a library with that id.
        return {"Error": constants.error_404_no_library}, 404

    if user_owns_library(dsClient, id, sub) is False:
        payload = {"Error": constants.error_403_no_access}
        status = 403
        return payload, status

    library["librarian"]["self"] = get_self(request, constants.users, library["librarian"]["id"])

    for book in library["books"]:

        book["self"] = get_self(request, constants.books, book["id"])

    return library, 200


# Returns a book with the provided id and self link.  Returns an error message if the entity is not found.
# Otherwise, returns a book entity along with a status code.
def get_book_with_status(dsClient, request, id):

    book, status = get_entity_with_info(dsClient, request, constants.books, id)

    if status == 404:
        # We couldn't find a book with that id.
        return {"Error": constants.error_404_no_book}, 404

    if book["library"] is not None:

        book["library"]["self"] = get_self(request, constants.libraries, book["library"]["id"])

    return book, 200


# Returns a list of all occurrences of a given kind of entity with id and self link included.
def get_entity_list(dsClient, request, kindOfEntity):

    query = dsClient.query(kind=kindOfEntity)
    results = list(query.fetch())
    for e in results:
        e["id"] = str(e.key.id)
        e["self"] = get_self(request, kindOfEntity, e["id"])
    return results, 200


def get_user_list(dsClient, request):

    return get_entity_list(dsClient, request, constants.users)


# Return a list of all libraries where the librarian's unique_id matches the user's JWT sub value.
def get_owner_library_list(dsClient, request, sub):

    # https://googleapis.dev/python/datastore/latest/client.html#google.cloud.datastore.client.Client.query
    query = dsClient.query(kind=constants.libraries)
    query.add_filter("librarian.unique_id", "=", sub)
    results = list(query.fetch())

    for e in results:
        e["id"] = str(e.key.id)
        e["self"] = get_self(request, constants.libraries, e["id"])
    return results, 200


# Deletes an entity of the provided type and id.  Returns the error "404 Not Found" and an error message
# if no such entity exists.  Returns "204 No Content" if deleted successfully.
def delete_entity(dsClient, kindOfEntity, errorMessage, id):

    entity_key = dsClient.key(kindOfEntity, int(id))
    entity = dsClient.get(key=entity_key)

    # https://realpython.com/null-in-python/
    if entity is None:
        # We couldn't find a boat with that id.
        return {"Error": errorMessage}, 404

    dsClient.delete(entity_key)

    return "", 204


def delete_library(dsClient, id, sub):

    library_key = dsClient.key(constants.libraries, int(id))
    library = dsClient.get(key=library_key)

    # https://realpython.com/null-in-python/
    if library is None:
        # We couldn't find a library with that id.
        return {"Error": constants.error_404_no_library}, 404

    elif user_owns_library(dsClient, id, sub) is False:

        return {"Error": constants.error_403_no_access}, 403

    # Similar structure as our Viewing Reservations example in Demo of Intermediate REST API Features in Python
    # adjusted to change my book values.
    for book in library["books"]:
        book_key = dsClient.key(constants.books, int(book["id"]))
        book_entity = dsClient.get(key=book_key)
        book_entity["library"] = None
        dsClient.put(book_entity)

    dsClient.delete(library_key)

    return "", 204


def delete_book(dsClient, id):

    book_key = dsClient.key(constants.books, int(id))
    book = dsClient.get(key=book_key)

    # https://realpython.com/null-in-python/
    if book is None:
        # We couldn't find a book with that id.
        return {"Error": constants.error_404_no_book}, 404

    if book["library"] is not None:

        library_key = dsClient.key(constants.books, int(id))
        library = dsClient.get(key=library_key)

        # Remove our book from the library
        # https://www.geeksforgeeks.org/python-removing-dictionary-from-list-of-dictionaries/
        # https://docs.python.org/3/library/stdtypes.html#range
        for i in range(len(library["books"])):

            if library["books"][i]["id"] == id:
                del library["books"][i]
                dsClient.put(library)
                break

    dsClient.delete(book_key)

    return "", 204


# Updates a kindOfEntity that has the provided id.
# Returns None with a status of 404 if no such entity with that id exists. Otherwise, returns the updated entity with
# a 200 status code.
def update_entity(dsClient, request, content, listOfKeys, kindOfEntity, id):

    entity = dsClient.get(key=dsClient.key(kindOfEntity, int(id)))

    # https://realpython.com/null-in-python/
    if entity is None:
        # We couldn't find a entity with that id.
        return None, 404

    newInfo = fill_entity(content, listOfKeys)
    entity.update(newInfo)
    dsClient.put(entity)

    entity["id"] = str(entity.key.id)
    entity["self"] = get_self(request, kindOfEntity, entity["id"])

    return entity, 200


# Method to simplify the library update.  Returns a library and 200 status if everything went smoothly.
# Returns an error message and 404 status if the id does not belong to a library.
# Returns an error message and 403 status if the library does not belong to the user.
# The library will be returned with it's id and self attributes added.
def update_library(dsClient, request, attributesToChange, id, sub):

    content = request.get_json()

    library, status = update_entity(dsClient, request, content, attributesToChange, constants.libraries, id)

    if status == 404:

        library = {"Error": constants.error_404_no_library}

    elif user_owns_library(dsClient, id, sub) is False:

        library = {"Error": constants.error_403_no_access}
        status = 403

    return library, status


# Patches parts of an library entity.  The library may have any attribute updated expect for id or attributes related
# to a relationship with other entities.
# Attempting to patch a library that doesn't belong to the user will return an error message and 403 status.
# An invalid id will return an error message and 404 status.
def patch_library(dsClient, request, id, sub):

    content = request.get_json()

    potential_keys = ["name", "street_address", "county", "state"]
    keysFound = getValidKeys(content, potential_keys)

    return update_library(dsClient, request, keysFound, id, sub)


# Patches an entire library entity.  The library will update every attribute except the id or attributes related to
# a relationship with other entities.
# Attempting to patch a library that doesn't belong to the user will return an error message and 403 status.
# An invalid id will return an error message and 404 status.
def put_library(dsClient, request, id, sub):

    keysExpected = ["name", "street_address", "county", "state"]

    return update_library(dsClient, request, keysExpected, id, sub)


# Method to simplify the books update.  Returns a book and 200 status if everything went smoothly.
# Returns an error message and 404 status if the id does not belong to a book.
# The book will be returned with it's id and self attributes added.
def update_book(dsClient, request, attributesToChange, id):

    content = request.get_json()

    library, status = update_entity(dsClient, request, content, attributesToChange, constants.books, id)

    if status == 404:

        library = {"Error": constants.error_404_no_book}

    return library, status


# Patches parts of an book entity.  The book may have any attribute updated expect for id or attributes related
# to a relationship with other entities.
# An invalid id will return an error message and 404 status.
def patch_book(dsClient, request, id):

    content = request.get_json()

    potential_keys = ["title", "author", "illustrator"]
    keysFound = getValidKeys(content, potential_keys)

    return update_book(dsClient, request, keysFound, id)


# Patches an entire book entity.  Must change the title, author, and illustrator.
# An invalid id will return an error message and 404 status.
def put_book(dsClient, request, id):

    content = request.get_json()

    keysExpected = ["title", "author", "illustrator"]

    return update_book(dsClient, request, keysExpected, id)


# Returns a list of all valid keys found.
def getValidKeys(content, listOfKeysExpected):

    listToReturn = []

    for key in content.keys():

        if key in listOfKeysExpected:

            listToReturn.append(key)

    return listToReturn


# Constructs the link for this entity's url.
def get_self(request, name, id):

    return request.url_root + name + "/" + str(id)


# Returns true if a library with this id exists.  Returns false, otherwise.
def library_exists(dsClient, id):

    library_key = dsClient.key(constants.libraries, int(id))
    library = dsClient.get(key=library_key)

    if library is None:

        return False

    return True


# Returns true if a book with this id exists.  Returns false, otherwise.
def book_exists(dsClient, id):

    library_key = dsClient.key(constants.libraries, int(id))
    library = dsClient.get(key=library_key)

    if library is None:

        return False

    return True


# Returns a list of all occurrences of a library with id and self link included.
# Also adds the self link to every libraries's books.
# Now have to add pagination
# { next: link to next page
#   count: 3
#   libraries: [{lib1}, {lib2}, {lib3}] }
def get_library_page(dsClient, request, sub):

    # offset = int(request.args.get('offset', 0))

    # Convert sub to user id
    user_id = convert_sub_to_user_id(dsClient, sub)

    filter_criteria = "librarian.id"
    filter_value = user_id

    results, next_url, count = get_page_info(dsClient, request, constants.libraries, filter_criteria, filter_value)

    for library in results:

        library["id"] = str(library.key.id)
        library["self"] = get_self(request, constants.libraries, library["id"])

        for book in library["books"]:

            book["self"] = get_self(request, constants.books, book["id"])

    output = {"next": next_url, "count": count, "libraries": results}

    return output, 200


# Returns a list of all occurrences of a load with id and self link included.
# Also adds the self link for the carrier of each load.
# Now have to add pagination
# { next: link to next page
#   loads: [{load1}, {load2}, {load3}] }
def get_book_page(dsClient, request):

    # offset = int(request.args.get('offset', 0))

    results, next_url, count = get_page_info(dsClient, request, constants.books)

    for book in results:
        book["id"] = str(book.key.id)
        book["self"] = get_self(request, constants.books, book["id"])

        if book["library"] is not None:
            book["library"]["self"] = get_self(request, constants.books, book["library"]["id"])

    output = {"next": next_url, "count": count, "books": results}

    return output, 200


# Gets all the page information for a given entity.  You may add one filtering criteria for the page using the
# filter_criteria and filter_value parameters.
# Returns the resulting page, next_url, and count of total entities in all the pages.
# This version has a limit of 5 items per page.
def get_page_info(dsClient, request, type, filter_criteria=None, filter_value=None):

    limit = 5
    # http://classes.engr.oregonstate.edu/eecs/perpetual/cs493-400/modules/4-more-rest-api-creation/5-use-demo-python/
    q_offset = int(request.args.get('offset', 0))
    query = dsClient.query(kind=type)

    if filter_criteria is not None and filter_value is not None:

        query.add_filter(filter_criteria, "=", filter_value)

    count = len(list(query.fetch()))

    l_iterator = query.fetch(limit=limit, offset=q_offset)
    pages = l_iterator.pages
    results = list(next(pages))

    if l_iterator.next_page_token:

        next_offset = q_offset + 5
        next_url = request.base_url + "?limit=" + str(limit) + "&offset=" + str(next_offset)

    else:

        next_url = None

    return results, next_url, count


# Returns true if the sub value matches a user in datastore.  Returns false, otherwise.
def sub_matches_user(dsClient, sub):

    query = dsClient.query(kind=constants.users)
    query.add_filter("unique_id", "=", sub)

    results = list(query.fetch())

    if len(results) == 1:

        return True

    return False


# Returns true if the application is requesting JSON for the returned body.
# Returns false, otherwise.
def is_requesting_json(request):

    # Demonstrated in lecture material
    if 'application/json' in request.accept_mimetypes:

        return True

    return False


# Place a book in a library.
def put_book_in_library(dsClient, request, library_id, book_id, sub):

    library, library_status = get_library_with_status(dsClient, request, library_id, sub)

    book, book_status = get_book_with_status(dsClient, request, book_id)

    if library_status == 404 or book_status == 404:

        return {"Error": constants.error_404_put}, 404

    elif book["library"] is not None or library_status == 403:

        return {"Error": constants.error_403_put}, 403

    # Update our book with the library's information.
    book["library"] = {
        "id": library["id"]
    }
    dsClient.put(book)

    # Add our book to the library.
    library["books"].append({"id": book["id"]})
    dsClient.put(library)

    return '', 204


def remove_book_from_library(dsClient, request, library_id, book_id, sub):

    library, library_status = get_library_with_status(dsClient, request, library_id, sub)

    book, book_status = get_book_with_status(dsClient, request, book_id)

    ids_match = book["library"] is not None and book["library"]["id"] == library["id"]

    if library_status == 404 or book_status == 404 or ids_match is False:

        return {"Error": constants.error_404_delete}, 404

    elif library_status == 403:

        return {"Error": constants.error_403_delete}, 403

    # Remove the library.
    book["library"] = None
    dsClient.put(book)

    # Remove our book from the library
    # https://www.geeksforgeeks.org/python-removing-dictionary-from-list-of-dictionaries/
    # https://docs.python.org/3/library/stdtypes.html#range
    for i in range(len(library["books"])):

        if library["books"][i]["id"] == book_id:
            del library["books"][i]
            dsClient.put(library)
            break

    return "", 204


# Returns true if the user owns the library.  Returns false, otherwise.
def user_owns_library(dsClient, library_id, sub):

    query = dsClient.query(kind=constants.users)
    query.add_filter("unique_id", "=", sub)

    user = list(query.fetch())[0]

    for library in user["libraries"]:

        if library["id"] == library_id:

            return True

    return False


# Converts a sub value into a user id to make it easier for queries
def convert_sub_to_user_id(dsClient, sub):

    query = dsClient.query(kind=constants.users)
    query.add_filter("unique_id", "=", sub)

    user = list(query.fetch())[0]

    return user.key.id
