from flask import Flask, render_template
import grpc
import raft_pb2
import raft_pb2_grpc
import pymongo
from datetime import datetime

app = Flask(__name__)

# Configuration
NODES = [
    {'id': 0, 'port': 5000},
    {'id': 1, 'port': 5001},
    {'id': 2, 'port': 5002},
    {'id': 3, 'port': 5003},
    {'id': 4, 'port': 5004}
]
MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "raft"
COLLECTION_NAME = "logs"

def get_node_status(port):
    try:
        channel = grpc.insecure_channel(f'localhost:{port}')
        stub = raft_pb2_grpc.RaftServiceStub(channel)
        response = stub.Status(raft_pb2.StatusRequest())
        return {
            'status': 'online',
            'state': response.state,
            'term': response.current_term,
            'logs': response.log_count,
            'is_leader': response.is_leader
        }
    except:
        return {'status': 'offline', 'state': 'unknown', 'term': -1, 'logs': 0}

@app.route('/')
def index():
    nodes_status = []
    for node in NODES:
        status = get_node_status(node['port'])
        status['port'] = node['port']
        status['id'] = node['id']
        nodes_status.append(status)
    
    # Get logs from MongoDB
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    logs = list(db[COLLECTION_NAME].find().sort('timestamp', -1).limit(10))
    client.close()
    
    return render_template('index.html', nodes=nodes_status, logs=logs)

if __name__ == '__main__':
    app.run(port=8080, debug=True)