import os
import sys
import multiprocessing
import config
from raft_node import Node  # Assuming Node class is defined in raft_node.py

def run_node(node_id, port, peers, db_uri, db_name, db_collection):
    # Create a Node instance and start the server
    node = Node(node_id=node_id, db_uri=db_uri, db_name=db_name, db_collection=db_collection)

    # Start the gRPC server for the node
    node.run(port)  # You should implement this method in the Node class

if __name__ == "__main__":
    # Get configuration parameters from config.py
    cfg = config.get_config()

    # Extract configuration for better readability
    node_id = cfg['node_id']
    port = cfg['port']
    peers = cfg['peers']
    db_uri = cfg['db_uri']
    db_name = cfg['db_name']
    db_collection = cfg['db_collection']

    # Create a process for each node
    processes = []

    for id in range(len(peers)):
        # Use the same peer list for each node, adjusting based on node_id
        current_peers = [f"localhost:{5000 + i}" for i in range(len(peers))]

        # Create a new process for each node
        proc = multiprocessing.Process(target=run_node, args=(id, 5000 + id, current_peers, db_uri, db_name, db_collection))
        processes.append(proc)
        proc.start()  # Start the node process

    # Optionally: Wait for all processes to finish (non-blocking), or implement signal handling
    for proc in processes:
        proc.join()  # This blocks until the process is finished; you might want to manage termination more gracefully

    print("All nodes have been started.")