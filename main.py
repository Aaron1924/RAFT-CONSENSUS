import multiprocessing
import config
from dotenv import load_dotenv
import os
import argparse
import time
from raft_node import Node  # Assuming Node class is defined in raft_node.py

def run_node(node_id, port, peers, db_uri, db_name, db_collection):
    time.sleep(1*node_id)  # Add a delay to stagger node startup
    node = Node(node_id=node_id, db_uri=db_uri, db_name=db_name, db_collection=db_collection)
    node.peers = peers # Pass the peers directly
    node.run(port)

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run a Raft node.")
    parser.add_argument('--node_id', type=int, required=True, help="The ID of the node.")
    parser.add_argument('--port', type=int, default=5000, help="The port on which the node will run.")
    parser.add_argument('--peers', nargs='+', required=True, help="List of peer addresses.")
    parser.add_argument('--db_uri', default=os.getenv('MONGODB_URI'), help="The URI of the MongoDB database.")
    parser.add_argument('--db_name', default=os.getenv('DB_NAME', 'raft'), help="The name of the MongoDB database.")
    parser.add_argument('--num_nodes', type=int, default=5, help="The total number of nodes in the cluster.")
    parser.add_argument('--db_collection', default=os.getenv('COLLECTION_NAME', 'logs'), help="The name of the MongoDB collection.")

    args = parser.parse_args()

    peers = [f'localhost:{args.port + i}' for i in range(args.num_nodes)]  # Create peers list here
    # Create a process for each node
    processes = []
    for id in range(args.num_nodes):  # Iterate using num_nodes
        port = args.port + id
        print(f"Node {id} will run on port {port}.")
        proc = multiprocessing.Process(target=run_node, args=(id, port, peers, args.db_uri, args.db_name, args.db_collection))
        processes.append(proc)
        proc.start()

    try:
        for proc in processes:
            proc.join()
    except KeyboardInterrupt:
        print("Shutting down nodes...")  # Informative message
        for proc in processes:  # Terminate node processes
            proc.terminate()

    print("All nodes have been started (or terminated).")