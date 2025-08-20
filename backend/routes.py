from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

def rewrite_oid(cursorList):
    cursorList['$id'] = cursorList['id']
    del cursorList['_id']
    return cursorList

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return jsonify(dict(status="OK")), 200

@app.route("/count", methods=['GET'])
def count():
    """return length of data"""
    song_count = db.songs.count_documents({})
    if song_count:
        return jsonify(count=song_count), 200

    return {"message": "Internal server error"}, 500

@app.route('/song', methods=['GET'])
def songs():
    songs = []
    for s in db.songs.find({}):
        # print(s)
        rewrite_oid(s)
        # print(s)
        songs.append(s)

    if songs:
        print(songs)
        return jsonify({"songs":songs}), 200

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    song = db.songs.find_one({"id": id})
    
    if song:
        rewrite_oid(song)
        return jsonify(song), 200

    return {"message": "song with id not found"}, 404

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    song = db.songs.find_one({"id": id})
    update = parse_json(request.get_json())

    if song != None:
        print(song)
        s = db.songs.update_one(song, {"$set": update})
        # song.save()
        if s.matched_count != s.modified_count or s.modified_count == None:
            print(s.matched_count)
            print(s.raw_result)
            print(s.modified_count)
            return {"message":"song found, but nothing updated"}, 200

        print(s.raw_result)
        return jsonify({"inserted_id": {"$oid": str(song['_id'])}}), 201

    return {"message": "song not found"}, 404


@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    deleted = db.songs.delete_one({"id":id})
    
    if deleted.deleted_count == 1:    
        return {}, 204

    return {"message": "song not found"}, 404

@app.route('/song', methods=['POST'])
def create_song():
    song = parse_json(request.get_json())

    test = db.songs.find_one({"id":song['id']})
    if test == None:
        s = db.songs.insert_one(song)
        return jsonify({"inserted_id": {"$oid": str(s.inserted_id)}}), 201

    return {"Message": "song with id {song['id']} already present"}, 302
