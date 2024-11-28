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
[MongoDB Installation](https://www.mongodb.com/try/download/community)


choose the appropriate version for your operating system, setup the server 

4. Run the following command to run the program
```bash
cd RAFT-CONSENSUS
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto # Generate the gRPC files
```

5. Run the following command to start the server
```bash
python main.py --node_id 0 --port 5000 --peers localhost:5001 localhost:5002 localhost:5003 localhost:5004 localhost:5005 --db_uri mongodb://localhost:27017
```

6. Run the following command to start the web app status
```bash
py app.py 
```





