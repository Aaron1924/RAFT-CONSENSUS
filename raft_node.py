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
        self.state = "follower"
        self.current_term = 0
        self.voted_for = None
        self.log = []  # In-memory log
        self.commit_index = 0
        self.last_applied = 0
        self.last_applied_index = 0
        node_db_name = f"{db_name}_node_{node_id}"
        self.db = raft_database.Database(db_uri, node_db_name, db_collection)
        self.peers = {}
        self.lock = threading.Lock()
        self.running = True
        self.port = None  # Port for the gRPC server
        

        self.recover_data()
        #threading.Thread(target=self.heartbeat, daemon=True).start()  # Start heartbeat thread
    
    
    def start_election(self):
        with self.lock:  # Essential for thread safety
            if self.state != "leader": # Only start election if not already leader. This prevents multiple leaders.
                self.state = "candidate"
                self.current_term += 1
                self.voted_for = self.node_id
                votes_received = 1

                for peer in self.peers:
                    try:
                        with grpc.insecure_channel(peer) as channel:
                            stub = raft_pb2_grpc.RaftServiceStub(channel)
                            request = raft_pb2.RequestVoteRequest(
                                term=self.current_term,
                                candidateId=self.node_id,
                                lastLogIndex=len(self.log) -1, # Correct lastLogIndex
                                lastLogTerm=self.log[-1].term if self.log else 0 # Correct lastLogTerm
                            )
                            response = stub.RequestVote(request)
                            if response.voteGranted:
                                votes_received += 1

                    except grpc.RpcError as e:
                        logging.error(f"Error requesting vote from {peer}: {e}")
                        continue # Important to avoid crashing. Handle the exception and continue.

                if votes_received > len(self.peers) // 2:
                    self.state = "leader"
                    logging.info(f"Node {self.node_id} became leader for term {self.current_term}")
                    self.election_timer.cancel()  # Stop the timer
                    self.start_heartbeat()  # Start heartbeat
                else:
                     self.state = 'follower' # Transition back to follower if election fails.
                     # Restart election timer with randomization
                     self.reset_election_timer()



    def reset_election_timer(self):
        timeout = random.uniform(0.15, 0.3)  # 150ms to 300ms
        self.election_timer = threading.Timer(timeout, self.start_election)
        self.election_timer.start()


    
    
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
        with self.lock:
            response = raft_pb2.RequestVoteResponse()
            if request.term > self.current_term:
                self.become_follower(request.term)  # Become follower if term is greater.

            if (self.voted_for is None or self.voted_for == request.candidateId) and \
               request.lastLogIndex >= len(self.log) - 1:  # Check log completeness
                response.voteGranted = True
                self.voted_for = request.candidateId
                self.reset_election_timer()  # Reset timer on receiving vote requests.
            else:
                response.voteGranted = False
                
            response.term = self.current_term
            return response
    
    
    def become_follower(self, term): # Helper method for transitioning to follower state.
        with self.lock:
            self.state = "follower"
            self.current_term = term
            self.voted_for = None
            self.reset_election_timer() # Ensure election timer is restarted if we revert from a candidate or leader state.

    def AppendEntries(self, request, context):
        with self.lock:
            response = raft_pb2.AppendEntriesResponse()
            if request.term > self.current_term:
                self.become_follower(request.term)  # Become follower if term is greater.

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
                with self.lock:
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
        self.port = port  # Store the port the server is running on.
        server.start()
        self.reset_election_timer()  # Start election timer *after* the server starts.
        logging.info(f"Node {self.node_id} is listening on port {port}")

        try:
            server.wait_for_termination()
        except KeyboardInterrupt: # Allow graceful shutdown with Ctrl+C.
            logging.info(f"Shutting down Node {self.node_id}")
            self.running = False  # Signal the heartbeat loop to stop.
            server.stop(5)  # Give the server 5 seconds to gracefully stop.
        
    def create_client(self, peer_address):
        """Create a gRPC client connection to a peer node."""
        channel = grpc.insecure_channel(peer_address)
        return raft_pb2_grpc.RaftServiceStub(channel)

    def query_peer_status(self, peer_address):
        """Query the status of a peer node."""
        client = self.create_client(peer_address)
        response = client.Status(raft_pb2.StatusRequest())
        return response
            
    def Status(self, request, context):
        return raft_pb2.StatusResponse(
            state=self.state,
            current_term=self.current_term,
            log_count=len(self.log),
            is_leader=(self.state == "leader")
        )
    
    def start_heartbeat(self):
        """Start the heartbeats for leader nodes."""
        while True:
            time.sleep(2)  # Heartbeat interval
            if self.state == "leader":
                for peer in self.peers:
                    self.send_heartbeat(peer)  # Call to send heartbeat to peers

    def send_heartbeat(self, peer):
        client = self.create_client(peer)
        try:
            response = client.Heartbeat(raft_pb2.HeartbeatRequest(term=self.current_term, leaderId=self.node_id))
            logging.info(f"Heartbeat sent from {self.node_id} to {peer}. Response: {response.success}")
        except grpc.RpcError as e:
            logging.error(f"Failed to send heartbeat to {peer}: {e}")
                    
        

    def close(self):
        self.db.close()
        self.running = False  # Use the existing gRPC server reference if needed
        
        
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