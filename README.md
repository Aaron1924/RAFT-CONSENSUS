# RAFT-CONSENSUS

## INSTRUCTIONS
1. Clone the repository
2. Run the following command to install the dependencies
```bash
py -m venv .venv
source .venv/bin/activate  # For Linux/macOS
.venv\Scripts\activate  # For Windows
pip install -r requirements.txt
```
3. Install mongodb and run the following command to start the server
[MongoDB Installation](https://www.mongodb.com/try/download/community-edition/releases?msockid=3b0ac080b3126d3c0845d5b4b2746c1a)
choose the appropriate version for your operating system, setup the server 

4. Run the following command to run the program
```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto # Generate the gRPC files
# Start Node 0
python raft_node.py --node_id 0 --port 5000 --peers localhost:5001 localhost:5002 localhost:5003 localhost:5004 --db_uri mongodb://localhost:27017

# Start Node 1
python raft_node.py --node_id 1 --port 5001 --peers localhost:5000 localhost:5002 localhost:5003 localhost:5004 --db_uri mongodb://localhost:27017

# Start Node 2
python raft_node.py --node_id 2 --port 5002 --peers localhost:5000 localhost:5001 localhost:5003 localhost:5004 --db_uri mongodb://localhost:27017

# Start Node 3
python raft_node.py --node_id 3 --port 5003 --peers localhost:5000 localhost:5001 localhost:5002 localhost:5004 --db_uri mongodb://localhost:27017

# Start Node 4
python raft_node.py --node_id 4 --port 5004 --peers localhost:5000 localhost:5001 localhost:5002 localhost:5003 --db_uri mongodb://localhost:27017
```


