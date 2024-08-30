from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Database configurations
LOCAL_MONGODB_URL = 'mongodb://localhost:27017'
LIBRARY_COLLECTION_LOCAL = "DataCenterLibrary"

ONLINE_MONGODB_URL = "mongodb+srv://amityaduvanshi:MMWMmrGaufkmvRJG@datacenter.gxlpazn.mongodb.net/?retryWrites=true&w=majority&appName=DataCenter"
DATABASE_NAME = "QubridDataCenter"
USER_COLLECTION_NAME = "DataCenterUsers"
DATA_COLLECTION_NAME = "DataCenterImages"
LIBRARY_COLLECTION_NAME = "DataCenterLibrary"


# Configure local MongoDB
local_client = MongoClient(LOCAL_MONGODB_URL)
local_db = local_client['UserDB']
local_users_collection = local_db['users']
local_library_collection= local_db[LIBRARY_COLLECTION_LOCAL]


# Configure online MongoDB
online_client = MongoClient(ONLINE_MONGODB_URL)
online_db = online_client[DATABASE_NAME]
online_users_collection = online_db[USER_COLLECTION_NAME]
online_data_collection = online_db[DATA_COLLECTION_NAME]
online_library_collection= online_db[LIBRARY_COLLECTION_NAME]

##############################
@app.route('/get_data', methods=['GET'])
def get_data():
    try:
        # Retrieve all documents from both local and online library collections
        local_documents = list(local_library_collection.find())
        online_documents = list(online_library_collection.find())
        
        # Convert ObjectId to string for JSON serialization
        for doc in local_documents + online_documents:
            doc['_id'] = str(doc['_id'])
        
        return jsonify(local_documents + online_documents), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/library_data', methods=['GET'])
def library_data():
    try:
        # Retrieve all documents from both local and online library collections
        local_documents = list(local_library_collection.find())
        online_documents = list(online_library_collection.find())
        
        # Convert ObjectId to string for JSON serialization
        for doc in local_documents + online_documents:
            doc['_id'] = str(doc['_id'])
        
        return jsonify(local_documents + online_documents), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
