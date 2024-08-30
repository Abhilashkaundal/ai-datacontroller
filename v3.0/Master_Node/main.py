from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
from ping3 import ping
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
import json


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Database configurations
LOCAL_MONGODB_URL = 'mongodb://localhost:27017'
LIBRARY_COLLECTION_LOCAL = "DataCenterLibrary"
IMAGES_COLLECTION_LOCAL = "DataCenterImages"

ONLINE_MONGODB_URL = "mongodb+srv://amityaduvanshi:MMWMmrGaufkmvRJG@datacenter.gxlpazn.mongodb.net/?retryWrites=true&w=majority&appName=DataCenter"
DATABASE_NAME = "QubridDataCenter"
USER_COLLECTION_NAME = "DataCenterUsers"
IMAGES_COLLECTION_NAME = "DataCenterImages"
LIBRARY_COLLECTION_NAME = "DataCenterLibrary"


# Configure local MongoDB
local_client = MongoClient(LOCAL_MONGODB_URL)
local_db = local_client['UserDB']
local_users_collection = local_db['users']
local_library_collection= local_db[LIBRARY_COLLECTION_LOCAL]
local_nodes_collection = local_db['DATAcenter_nodes']
local_images_collection=local_db[IMAGES_COLLECTION_LOCAL]
# Configure online MongoDB
online_client = MongoClient(ONLINE_MONGODB_URL)
online_db = online_client[DATABASE_NAME]
online_users_collection = online_db[USER_COLLECTION_NAME]
online_images_collection = online_db[IMAGES_COLLECTION_NAME]
online_library_collection= online_db[LIBRARY_COLLECTION_NAME]
online_nodes_collection = online_db['DATAcenter_nodes']

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

@app.route('/user/register', methods=['POST'])
def register():
    """
    Register a new user.
    """
    try:
        # Check if any user already exists
        if local_users_collection.count_documents({}) > 0:
            return jsonify(success=False, message="Buy a license for more registration.please contact digital@qubrid.com"), 400

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # Validate email and password
        if not email or not password:
            return jsonify(success=False, message="Email and password are required."), 400

        # Validate email format
#        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
 #       if not re.match(email_regex, email):
  #          return jsonify(success=False, message="Invalid email format."), 400

        if len(password) < 8 or not any(char.isupper() for char in password) \
                or not any(char.islower() for char in password) \
                or not any(char.isdigit() for char in password):
            return jsonify(success=False, message="Password must be at least 8 characters long and include uppercase, lowercase, and a digit."), 400
        existing_local_user = local_users_collection.find_one({"email": email})

        if existing_local_user:
           return jsonify(success=False, message="User already registered."), 400
        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # User document
        user_doc = {
            "email": email,
            "password": hashed_password,
            "trial_start_date": datetime.utcnow(),
            "trial_end_date": datetime.utcnow() + timedelta(days=90)
        }

        # Insert new user into the local database
        local_users_collection.insert_one(user_doc)

        return jsonify(success=True, message="Registration successful."), 201

    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@app.route("/user/login", methods=["POST"])
def login():
    """
    Endpoint for user login.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify(success=False, message="Email and password are required."), 400

    user = local_users_collection.find_one({"email": email}) or online_users_collection.find_one({"email": email})

    if not user or not check_password_hash(user['password'], password):
        return jsonify(success=False, message="Login failed. Check email and/or password."), 401

   # if datetime.utcnow() > user['trial_end_date']:
    #    return jsonify(success=False, message="Trial period has ended."), 403
    days_remaining = (user['trial_end_date'] - datetime.utcnow()).days
    token = jwt.encode({'email': email, 'exp': datetime.utcnow() + timedelta(minutes=int(36000))}, "QubridLLC", algorithm="HS256")

    return jsonify(success=True, token=token, email=email, days_remaining=days_remaining), 200
###################################################################
# Function to fetch and update node info
def fetch_and_update_info(ip, route):
    try:
        result = subprocess.run(
            ["curl", f"http://{ip}:5000/{route}"],
            capture_output=True,
            text=True,
            check=True
        )
        info = json.loads(result.stdout)
        return info
    except subprocess.CalledProcessError as e:
            return {"error": str(e)}

@app.route('/add-node', methods=['POST'])
def add_node():
    data = request.json
    node_name = data.get('node_name')
    hostname = data.get('hostname')
    ip_address = data.get('ip_address')

    if not node_name or not hostname or not ip_address:
        return jsonify({"message": "Node name, hostname, and IP address are required"}), 400

    # Check for existing node in local database by node_name, hostname, or ip_address
    if local_nodes_collection.find_one({"$or": [{"node_name": node_name}, {"hostname": hostname}, {"ip_address": ip_address}]}):
        return jsonify({"message": "Node with this name, hostname, or IP address already exists in the local database"}), 400

    # Ping the IP address to determine the status
    status = "Running" if ping(ip_address) else "Stopped"

    # Fetch and update GPU, CPU, and RAM info
    gpu_info_response = fetch_and_update_info(ip_address, 'gpu_info')
    if 'error' in gpu_info_response:
        return jsonify({"error": "Failed to fetch GPU info: " + gpu_info_response['error']}), 500
    gpu_info = gpu_info_response.get('gpu_info', '')

    cpu_info_response = fetch_and_update_info(ip_address, 'cpu_info')
    if 'error' in cpu_info_response:
        return jsonify({"error": "Failed to fetch CPU info: " + cpu_info_response['error']}), 500
    cpu_info = cpu_info_response.get('cpu_info', '')

    ram_info_response = fetch_and_update_info(ip_address, 'ram_info')
    if 'error' in ram_info_response:
        return jsonify({"error": "Failed to fetch RAM info: " + ram_info_response['error']}), 500
    ram_info = ram_info_response.get('ram_info', '')

    # Node data
    node_data = {
        "node_name": node_name,
        "hostname": hostname,
        "ip_address": ip_address,
        "status": status,
        "gpu_info": gpu_info,
        "cpu_info": cpu_info,
        "ram_info": ram_info
    }

    # Insert node in both databases
    local_nodes_collection.insert_one(node_data)
    online_nodes_collection.insert_one(node_data)

    return jsonify({
        "message": "Node added successfully",
        "status": status,
        "gpu_info": gpu_info,
        "cpu_info": cpu_info,
        "ram_info": ram_info
    }), 201

def update_node_status():
    nodes = local_nodes_collection.find({})
    for node in nodes:
        ip_address = node.get('ip_address')
        status = "Running" if ping(ip_address) else "Stopped"

        # Update status in local database
        local_nodes_collection.update_one(
            {"ip_address": ip_address},
            {"$set": {"status": status}}
        )

        # Update status in online database
        online_nodes_collection.update_one(
            {"ip_address": ip_address},
            {"$set": {"status": status}}
        )

def update_gpu_info():
    nodes = local_nodes_collection.find({})
    for node in nodes:
        ip_address = node.get('ip_address')
        gpu_info_response = fetch_and_update_info(ip_address, 'gpu_info')
        if 'error' not in gpu_info_response:
            gpu_info = gpu_info_response.get('gpu_info', '')

            # Update GPU info in local database
            local_nodes_collection.update_one(
                {"ip_address": ip_address},
                {"$set": {"gpu_info": gpu_info}}
            )

            # Update GPU info in online database
            online_nodes_collection.update_one(
                {"ip_address": ip_address},
                {"$set": {"gpu_info": gpu_info}}
            )

# Scheduler to update node status every 5 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(update_node_status, 'interval', minutes=1)
scheduler.add_job(update_gpu_info, 'interval', minutes=1)
scheduler.start()

#############################################

@app.route('/get-nodes', methods=['GET'])
def get_nodes():
    try:
        # Retrieve all documents from the local nodes collection
        nodes = list(local_nodes_collection.find({}, {"_id": 0, "node_name": 1, "hostname": 1, "ip_address": 1, "status": 1, "gpu_info": 1, "cpu_info": 1, "ram_info": 1}))

        # Convert the documents to a list of dictionaries
        node_list = [node for node in nodes]

        return jsonify(node_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
################################################################
@app.route('/delete-node', methods=['POST'])
def delete_node():
    data = request.json
    node_name = data.get('node_name')
    ip_address = data.get('ip_address')

    if not node_name or not ip_address:
        return jsonify({"error": "Node name and IP address are required"}), 400

    # Check for existing node in local database by node_name and ip_address
    node = local_nodes_collection.find_one({"node_name": node_name, "ip_address": ip_address})
    if not node:
        return jsonify({"message": "Node with this name and IP address does not exist in the local database"}), 404

    # Delete node from both databases
    local_nodes_collection.delete_one({"node_name": node_name, "ip_address": ip_address})
    online_nodes_collection.delete_one({"node_name": node_name, "ip_address": ip_address})

    return jsonify({"message": "Node deleted successfully"}), 200
##################################################################################################
@app.route('/images_data', methods=['GET'])
def get_combined_data():
    try:
        # Get pagination parameters from query string
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Fetch documents from online data collection with pagination
        online_documents = list(online_images_collection.find({}).skip(skip).limit(limit))
        for doc in online_documents:
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string for JSON serialization

        # Fetch documents from local data collection with pagination
        local_documents = list(local_images_collection.find({}).skip(skip).limit(limit))
        for doc in local_documents:
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string for JSON serialization

        # Combine the documents
        combined_documents = {
            "online_data": online_documents,
            "local_data": local_documents
        }

        return jsonify(combined_documents), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
