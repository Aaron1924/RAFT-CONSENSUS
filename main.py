import multiprocessing
import config
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
    # Get configurations from config.py
    cfg = config.get_config()

    # Create a process for each node
    processes = []
    for id in range(len(cfg['peers'])):
        port = 5000 + id
        proc = multiprocessing.Process(target=run_node, args=(id, port, cfg['peers'], cfg['db_uri'], cfg['db_name'], cfg['db_collection']))
        processes.append(proc)
        proc.start()  # Start the node process

    # Optionally: wait for all processes to finish
    for proc in processes:
        proc.join()  # Block until each node process is finished

    print("All nodes have been started.")