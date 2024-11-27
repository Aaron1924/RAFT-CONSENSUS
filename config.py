import argparse

def get_config():
    parser = argparse.ArgumentParser(description='Raft Configuration')

    # Define the parameters required for the Raft nodes
    parser.add_argument('--node_id', type=int, required=True, help='ID of the node (0, 1, 2, ...)')
    parser.add_argument('--port', type=int, default=5000, help='Port for the node to listen on (default: 5000)')
    parser.add_argument('--peers', nargs='+', required=True, help='List of peer addresses (e.g., localhost:5001 localhost:5002)')

    # Database configuration
    parser.add_argument('--db_uri', type=str, required=True, help='MongoDB URI for the database')
    parser.add_argument('--db_name', type=str, default='raft_db', help='Database name (default: raft_db)')
    parser.add_argument('--db_collection', type=str, default='logs', help='Collection name for logs (default: logs)')

    args = parser.parse_args()

    return {
        'node_id': args.node_id,
        'port': args.port,
        'peers': args.peers,
        'db_uri': args.db_uri,
        'db_name': args.db_name,
        'db_collection': args.db_collection,
    }

if __name__ == "__main__":
    config = get_config()
    print("Configuration:")
    for key, value in config.items():
        print(f"{key}: {value}")