import os
import raft_node  # Ensure this import statement is present
import time
import logging
import threading
import grpc
from concurrent import futures
import raft_pb2_grpc  # Adjust import if needed
from dotenv import load_dotenv

def serve(node_instance, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServiceServicer_to_server(node_instance, server)  # Pass your node instance
    server.add_insecure_port(f'[::]:{port}')  # Use the provided port
    server.start()
    server.wait_for_termination()

def main():
    # Load configuration from .env file
    load_dotenv()
    db_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("DB_NAME")
    db_collection = os.getenv("COLLECTION_NAME")
    node_count = int(os.getenv("NODE_COUNT"))

    # Validate configuration.  Critical to catch issues early!
    if not db_uri:
        logging.critical("MONGODB_URI environment variable not set!")
        return
    if node_count < 1:
        logging.critical("NODE_COUNT must be a positive integer!")
        return

    # Initialize Raft nodes
    nodes = []
    base_port = 50051  # Starting port number
    for i in range(1, node_count + 1):
        node_instance = raft_node.Node(i, db_uri, db_name, db_collection)
        nodes.append((node_instance, base_port + i - 1))  # Assign a unique port to each node

    # Start the gRPC servers for each node:
    servers = []
    for node_instance, port in nodes:
        server_thread = threading.Thread(target=serve, args=(node_instance, port))
        servers.append(server_thread)
        server_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down servers...")
        for server in servers:
            server.join()
        for node_instance, _ in nodes:
            node_instance.close()
        print("Servers shut down.")

if __name__ == "__main__":
    main()