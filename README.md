# RAFT-CONSENSUS

## INSTRUCTIONS
1. Clone the repository
2. Run the following command to install the dependencies
```bash
pip install -r requirements.txt
```
3. Install mongodb and run the following command to start the server
[MongoDB Installation](https://www.mongodb.com/try/download/community)


choose the appropriate version for your operating system and setup the server 

4. Run the following command to run the program
```bash
cd RAFT-CONSENSUS
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto # Generate the gRPC files
```

5. Run the following command to start the server
```bash
 python main.py --node_id 0 --base_port 5000 --num_nodes 5 --db_uri mongodb://localhost:27017 --db_name raft --db_collection logs
```
the server will run on http://127.0.0.1:8080




