import multiprocessing
import config
from dotenv import load_dotenv
import os
import argparse
from raft_node import Node  # Assuming Node class is defined in raft_node.py

def run_node(node_id, port, peers, db_uri, db_name, db_collection):
    # Create a Node instance and run the server
    node = Node(node_id=node_id, db_uri=db_uri, db_name=db_name, db_collection=db_collection)

    # Initialize peers (including localhost addresses)
    node.peers = [f'localhost:{p}' for p in range(5000, 5000 + len(peers))]

    # Start the gRPC server for the node
    node.run(port)  # This starts the gRPC server

    # Start heartbeat for the leader node
    if node.state == "leader":
        node.start_heartbeat()  # This could be managed separately if needed.

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run a Raft node.")
    parser.add_argument('--node_id', type=int, required=True, help="The ID of the node.")
    parser.add_argument('--port', type=int, default=5000, help="The port on which the node will run.")
    parser.add_argument('--peers', nargs='+', required=True, help="List of peer addresses.")
    parser.add_argument('--db_uri', default=os.getenv('MONGODB_URI'), help="The URI of the MongoDB database.")
    parser.add_argument('--db_name', default=os.getenv('DB_NAME', 'raft'), help="The name of the MongoDB database.")
    parser.add_argument('--db_collection', default=os.getenv('COLLECTION_NAME', 'logs'), help="The name of the MongoDB collection.")

    args = parser.parse_args()

    # Create a process for each node
    processes = []
    for id in range(len(args.peers)):
        port = args.port + id
        proc = multiprocessing.Process(target=run_node, args=(id, port, args.peers, args.db_uri, args.db_name, args.db_collection))
        processes.append(proc)
        proc.start()  # Start the node process

    # Optionally: wait for all processes to finish
    for proc in processes:
        proc.join()  # Block until each node process is finished

    print("All nodes have been started.")