import time
import random
import uuid
import grpc
import logging
from concurrent import futures
import pymongo
import raft_pb2, raft_pb2_grpc
import raft_database
import threading



class Node(raft_pb2_grpc.RaftServiceServicer):
    def __init__(self, node_id, db_uri, db_name, db_collection):
        self.node_id = node_id
        self.current_term = 0
        self.voted_for = None
        self.log = []  # In-memory log
        self.commit_index = 0
        self.last_applied = 0
        self.state = "follower"
        self.election_timer = None
        self.last_applied_index = 0
        self.db = raft_database.Database(db_uri, db_name, db_collection)
        self.peers = {}
        self.lock = threading.Lock()
        self.heartbeat_interval = 1  # Heartbeat interval in seconds
        self.running = True
        self.port = port

        self.recover_data()
        threading.Thread(target=self.heartbeat, daemon=True).start()  # Start heartbeat thread

    def recover_data(self):
        # Load the log entries from the database sorted by index
        log_entries = []
        for entry in self.db.collection.find().sort("index", pymongo.ASCENDING):
            entry_obj = raft_pb2.LogEntry(
                term=entry['term'], 
                command=entry['command'].encode(),  # Ensure command is in bytes
                timestamp=entry['timestamp']
            )
            log_entries.append(entry_obj)
        self.log = log_entries
        self.last_applied_index = len(self.log)  # Set according to loaded logs

    def append_entry(self, entry):
        entry['index'] = len(self.log) + 1  # Assign the index
        entry['_id'] = str(uuid.uuid4())   # Unique ID for the entry
        self.db.append_entry(entry)          # Save to the database
        self.log.append(raft_pb2.LogEntry(term=entry['term'], command=entry['command'].encode(), timestamp=entry['timestamp']))

    def RequestVote(self, request, context):
        response = raft_pb2.RequestVoteResponse()
        if request.term > self.current_term:
            self.current_term = request.term
            self.voted_for = None
            self.state = "follower"  # Reset state on term increase
        # Voting logic
        if self.voted_for is None or self.voted_for == request.candidateId:
            response.term = self.current_term
            response.voteGranted = True
            self.voted_for = request.candidateId
        else:
            response.term = self.current_term
            response.voteGranted = False
        return response

    def AppendEntries(self, request, context):
        response = raft_pb2.AppendEntriesResponse()
        with self.lock:
            if request.term > self.current_term:
                self.current_term = request.term
                self.state = "follower"
                self.voted_for = None  # Reset voted_for to allow future elections

            # Verify the log's previous index and term
            if request.prevLogIndex < len(self.log) and self.log[request.prevLogIndex].term == request.prevLogTerm:
                # Valid log entry, append new entries
                for entry in request.entries:
                    self.append_entry({
                        "term": entry.term,
                        "command": entry.command.decode(),  # Convert back from bytes
                        "timestamp": entry.timestamp
                    })
                response.success = True
                response.matchIndex = len(self.log)  # The index of the last entry
            else:
                response.success = False

            response.term = self.current_term  # Respond with current term
            return response
    def Heartbeat(self, request, context):
        response = raft_pb2.HeartbeatResponse()
        response.term = self.current_term
        response.success = True
        return response
    def heartbeat(self):
        while self.running:
            if self.state == "leader":
                for peer in self.peers:
                    with grpc.insecure_channel(peer) as channel:
                        stub = raft_pb2_grpc.RaftServiceStub(channel)
                        try:
                            stub.Heartbeat(raft_pb2.HeartbeatRequest(term=self.current_term, leaderId=self.node_id))
                        except grpc.RpcError as e:
                            logging.error(f"Error sending heartbeat to {peer}: {e}")
            time.sleep(self.heartbeat_interval)
            
    
    def run(self, port):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        raft_pb2_grpc.add_RaftServiceServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        logging.info(f"Node {self.node_id} is listening on port {port}")
        server.wait_for_termination()  # Keep the server running
            
    def Status(self, request, context):
        return raft_pb2.StatusResponse(
            state=self.state,
            current_term=self.current_term,
            logs=self.log,
        )
                    
        

    def close(self):
        self.db.close()
        self.server.stop(0)  # Use the existing gRPC server reference if needed
        
        
import config

if __name__ == "__main__":
    cfg = config.get_config()
    node_id = cfg['node_id']
    port = cfg['port']
    peers = cfg['peers']
    db_uri = cfg['db_uri']
    db_name = cfg['db_name']
    db_collection = cfg['db_collection']

    # Initialize your Raft Node
    node = Node(node_id=node_id, db_uri=db_uri, db_name=db_name, db_collection=db_collection)

    # Start the gRPC server, etc...