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
def create_entity(dsClient, request, keysExpected, kindOfEntity):

    content = request.get_json()

    new_entity = datastore.entity.Entity(key=dsClient.key(kindOfEntity))

    newInfo = fill_entity(content, keysExpected)

    new_entity.update(newInfo)
    dsClient.put(new_entity)

    new_entity["id"] = str(new_entity.key.id)
    new_entity["self"] = get_self(request, kindOfEntity, new_entity["id"])

    return new_entity, 201


# Creates a user entity.  Returns the new entity as a json object along with a 201 created code on success.
# The returned json entity will also include the entity's id and self link.
def create_user(dsClient, request):

    keysExpected = ["unique_id"]

    return create_entity(dsClient, request, keysExpected, constants.libraries)


# Creates a library entity.  Returns the new entity as a json object along with a 201 created code on success.
# The returned json entity will also include the entity's id and self link.
def create_library(dsClient, request, owner_sub):

    content = request.get_json()

    keysExpected = ["name", "street_address", "county", "state"]

    new_library = datastore.entity.Entity(key=dsClient.key(constants.libraries))

    newInfo = fill_entity(content, keysExpected)

    query = dsClient.query(kind=constants.users)
    query.add_filter("unique_id", "=", owner_sub)

    librarian = list(query.fetch())[0]

    newInfo["librarian"] = {"id": librarian.key.id}

    new_library.update(newInfo)
    dsClient.put(new_library)

    new_library["id"] = str(new_library.key.id)
    new_library["self"] = get_self(request, constants.libraries, new_library["id"])

    return new_library, 201


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


# Returns a boat with the provided id and self link.  Returns an error message if the entity is not found.
# Otherwise, returns a boat entity along with a status code.
def get_library_with_status(dsClient, request, id):

    boat, status = get_entity_with_info(dsClient, request, constants.libraries, id)

    if status == 404:
        # We couldn't find a boat with that id.
        return {"Error": constants.error_404_no_library}, 404

    return boat, 200


# Returns a list of all occurrences of a given kind of entity with id and self link included.
def get_entity_list(dsClient, request, kindOfEntity):

    query = dsClient.query(kind=kindOfEntity)
    results = list(query.fetch())
    for e in results:
        e["id"] = str(e.key.id)
        e["self"] = get_self(request, kindOfEntity, e["id"])
    return results, 200


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

    elif library["sub"] != sub:

        return {"Error": constants.error_403_no_access}, 403

    dsClient.delete(library_key)

    return "", 204


# Updates a kindOfEntity that has the provided id.
# Returns None if no such entity with that id exists. Otherwise, returns the updated entity.
def update_entity(dsClient, content, listOfKeys, kindOfEntity, id):

    entity = dsClient.get(key=dsClient.key(kindOfEntity, int(id)))

    # https://realpython.com/null-in-python/
    if entity is None:
        # We couldn't find a boat with that id.
        return None

    newInfo = fill_entity(content, listOfKeys)
    entity.update(newInfo)
    dsClient.put(entity)

    return entity


# Patches parts of an boat entity.  The boat may have any attribute updated expect for id.
# Invalid input and extra attributes will return an error message and 400 status.
# The boat name that is not unique will return an error message and 403 status.
# An invalid id will return an error message and 404 status.
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


# Returns a list of all occurrences of a library with id and self link included.
# Also adds the self link to every libraries's books.
# Now have to add pagination
# { next: link to next page
#   count: 3
#   libraries: [{lib1}, {lib2}, {lib3}] }
def getLibraryPage(dsClient, request, owner):

    offset = int(request.args.get('offset', 0))

    filter_criteria = "librarian.unique_id"
    filter_value = owner

    results, next_url, count = getPageInfo(dsClient, request, constants.libraries, filter_criteria, filter_value)

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
def getBookPage(dsClient, request):

    offset = int(request.args.get('offset', 0))
    if offset < 0:

        return {"Error": constants.error_negative_offset}, 400

    results, next_url = getPageInfo(dsClient, request, constants.loads)

    for load in results:
        load["id"] = str(load.key.id)
        load["self"] = get_self(request, constants.loads, load["id"])

        if load["carrier"] is not None:
            load["carrier"]["self"] = get_self(request, constants.boats, load["carrier"]["id"])

    output = {"loads": results, "next": next_url}

    return output, 200


# Gets all the page information for a given entity.  You may add one filtering criteria for the page using the
# filter_criteria and filter_value parameters.
# Returns the resulting page, next_url, and count of total entities in all the pages.
# This version has a limit of 5 items per page.
def getPageInfo(dsClient, request, type, filter_criteria=None, filter_value=None):

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
def subMatchesUser(dsClient, sub):

    query = dsClient.query(kind=constants.users)
    query.add_filter("unique_id", "=", sub)

    results = list(query.fetch())

    if len(results) == 1:

        return True

    return False
