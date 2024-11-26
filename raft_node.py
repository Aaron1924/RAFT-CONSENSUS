import time
import random
import uuid
import grpc
import logging
from concurrent import futures
import pymongo
import raft_pb2, raft_pb2_grpc
import raft_database


class Node(raft_pb2_grpc.RaftService):
    def __init__(self, node_id, db_uri, db_name, db_collection):
        self.node_id = node_id
        self.current_term = 0
        self.voted_for = None
        self.log = []  # In-memory log
        self.commit_index = 0
        self.last_applied = 0
        self.state = "follower"
        self.election_timer = None  # For election timer
        self.last_applied_index = 0
        self.db = raft_database.Database(db_uri, db_name, db_collection)
        self.peers = {}  # Dictionary of peer nodes

    def recover_data(self):
      # ...
      # Get log from database sorted by index.
      # Load the log from the database and reconstruct the self.log.
      # Initialize last_applied and other critical state variables.
      log_entries = []
      for entry in self.db.collection.find().sort("index", pymongo.ASCENDING):
          log_entries.append(entry)
      self.log = log_entries
      self.last_applied_index = 0 # Important: Reset last_applied_index

    def append_entry(self, entry):
      entry['index'] = len(self.log) + 1  # Crucial: Assign the index
      entry['_id'] = str(uuid.uuid4())
      self.db.append_entry(entry)
      self.log.append(entry)



    def RequestVote(self, request, context):
        response = raft_pb2.RequestVoteResponse()
        if request.term > self.current_term:
            self.current_term = request.term
            self.voted_for = None
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
        return response
  
  
    def close(self):
        self.db.close()


# ... (Other functions, configuration) ...