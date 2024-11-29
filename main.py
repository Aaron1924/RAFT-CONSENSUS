import multiprocessing
import os
import argparse
import time
import grpc
import raft_pb2
import raft_pb2_grpc
from raft_node import Node
from flask import Flask, render_template, request, jsonify
import logging
from dotenv import load_dotenv # For env vars
from concurrent import futures # for gRPC server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Global variables for Raft cluster (initialized later)
base_port = None
num_nodes = None
db_uri = None
db_name = None
db_collection = None
peers = None
leader_port = None
processes = []


def run_node(node_id, port, peers, db_uri, db_name, db_collection):
    time.sleep(0.5 * node_id)  # Stagger startups
    node = Node(node_id=node_id, db_uri=db_uri, db_name=db_name, db_collection=db_collection)
    node.peers = peers
    node.run(port)



def get_node_status(node_id, port):
    try:
        with grpc.insecure_channel(f'localhost:{port}') as channel:
            stub = raft_pb2_grpc.RaftNodeStub(channel)  # Use correct stub name
            response = stub.Status(raft_pb2.StatusRequest())  # Use correct request name
            return {
                'node_id': node_id,
                'port': port,
                'state': response.state,
                'term': response.current_term,
                'last_log_index': response.last_log_index, # Ensure these match your .proto
                'peers': response.peers,
                'status': 'online',
            }
    except grpc.RpcError as e:
        logging.error(f"Error getting status from node {node_id} on port {port}: {e}")  # Log the error
        return {
            'node_id': node_id,
            'port': port,
            'state': 'unknown',
            'term': -1,
            'last_log_index': -1,
            'peers': [],
            'status': 'offline',
        }


@app.route('/', methods=['GET'])
def cluster_status():
    nodes_status = []
    for i in range(num_nodes):
        port = base_port + i
        status = get_node_status(i, port)
        nodes_status.append(status)
    return render_template('index.html', nodes=nodes_status)  # Assuming you have cluster.html



@app.route('/client_request', methods=['POST'])
def handle_client_request():  # Must be defined before used
    command = request.form.get('command')
    if leader_port is None:  # Handle the case where no leader is found
        return jsonify({'status': 'failure', 'message': 'No leader found'}), 500
    try:
        with grpc.insecure_channel(f'localhost:{leader_port}') as channel:
            stub = raft_pb2_grpc.RaftNodeStub(channel)
            response = stub.ClientCommand(raft_pb2.ClientRequest(command=command.encode())) # Encode to bytes
            if response.success:
                result = response.response.decode() if response.response else "Command executed successfully"
                return jsonify({'status': 'success', 'result': result})
            else:
                return jsonify({'status': 'failure', 'message': response.response.decode()}), 500  # Include error message from Raft node
    except grpc.RpcError as e:
        return jsonify({'status': 'failure', 'message': f'gRPC error: {e}'}), 500




if __name__ == "__main__":
    load_dotenv()  # Load environment variables

    parser = argparse.ArgumentParser(description="Run a Raft cluster with web UI.")
    parser.add_argument('--node_id', type=int, required=True, help="The ID of this node.")
    parser.add_argument('--base_port', type=int, default=5000, help="The base port for the cluster.")
    parser.add_argument('--num_nodes', type=int, default=5, help="The total number of nodes in the cluster.")
    parser.add_argument('--db_uri', default=os.getenv('MONGODB_URI'), help="MongoDB URI.")
    parser.add_argument('--db_name', default=os.getenv('DB_NAME', 'raft'), help="MongoDB database name.")
    parser.add_argument('--db_collection', default=os.getenv('COLLECTION_NAME', 'logs'), help="MongoDB collection name.")

    args = parser.parse_args()
    base_port = args.base_port
    num_nodes = args.num_nodes
    db_uri = args.db_uri
    db_name = args.db_name
    db_collection = args.db_collection
    peers = [f'localhost:{base_port + i}' for i in range(num_nodes)]

    # ... (Start Raft nodes - no changes)


    # Find the leader - simplified
    leader_port = None
    for port in range(base_port, base_port + num_nodes):
        try:
            with grpc.insecure_channel(f'localhost:{port}') as channel:
                stub = raft_pb2_grpc.RaftServiceStub(channel)
                status = stub.Status(raft_pb2.StatusRequest())
                if status.state == "leader":
                    leader_port = port
                    logging.info(f"Leader found on port: {leader_port}")  # Log the leader
                    break  # Exit loop once leader is found
        except grpc.RpcError as e:
             logging.warning(f"Error checking for leader on port {port}: {e}") # Log the error but continue checking


    if leader_port is None:
        logging.error("No leader found after initial check.")
    

    app.run(debug=True, port=8080, use_reloader=False, host='0.0.0.0')

    # ...graceful shutdown (no changes needed here)