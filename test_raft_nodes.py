import unittest
import time
import grpc
import pymongo
from dotenv import load_dotenv
import os
import raft_pb2
import raft_pb2_grpc
from raft_node import Node
import threading
import logging

class TestRaftNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Load environment variables
        load_dotenv()
        
        # MongoDB configuration
        cls.db_uri = "mongodb://localhost:27017"
        cls.db_name = "raft_test"
        cls.db_collection = "test_logs"
        
        # Clear test database
        client = pymongo.MongoClient(cls.db_uri)
        client[cls.db_name][cls.db_collection].delete_many({})
        
        # Node configuration
        cls.base_port = 5000
        cls.num_nodes = 5
        cls.peers = [f'localhost:{cls.base_port + i}' for i in range(cls.num_nodes)]

    def setUp(self):
        self.nodes = []
        self.node_threads = []
        
        # Create and start nodes
        for i in range(self.num_nodes):
            node = Node(
                node_id=i,
                db_uri=self.db_uri,
                db_name=self.db_name,
                db_collection=self.db_collection
            )
            node.peers = self.peers
            self.nodes.append(node)
            
            # Start node in separate thread
            thread = threading.Thread(
                target=node.run,
                args=(self.base_port + i,)
            )
            thread.daemon = True
            thread.start()
            self.node_threads.append(thread)
        
        # Wait for nodes to start
        time.sleep(2)

    def tearDown(self):
        for node in self.nodes:
            node.close()
        time.sleep(1)
        
        if hasattr(self, 'client'):
            self.client.close()

    def test_node_initialization(self):
        """Test if nodes are properly initialized"""
        for i, node in enumerate(self.nodes):
            self.assertEqual(node.node_id, i)
            self.assertEqual(node.state, "follower")
            self.assertEqual(node.current_term, 0)
            self.assertIsNone(node.voted_for)

    
    def test_leader_election_scenario(self):
        """Test the complete leader election process"""
        # Initial state check - all should be followers
        for node in self.nodes:
            self.assertEqual(node.state, "follower")
        
        # Select node 0 to become candidate
        candidate_node = self.nodes[0]
        candidate_node.state = "candidate"
        
        # Increment term and request votes
        candidate_node.current_term += 1
        for peer in candidate_node.peers:
            try:
                channel = grpc.insecure_channel(peer)
                stub = raft_pb2_grpc.RaftServiceStub(channel)
                
                # Create vote request
                request = raft_pb2.RequestVoteRequest(
                    term=candidate_node.current_term,
                    candidateId=candidate_node.node_id,
                    lastLogIndex=len(candidate_node.log),
                    lastLogTerm=candidate_node.current_term
                )
                
                # Send vote request
                response = stub.RequestVote(request)
                logging.info(f"Vote response from {peer}: {response.voteGranted}")
                
            except grpc.RpcError as e:
                logging.error(f"Failed to request vote from {peer}: {e}")
        
        # Wait for voting to complete
        time.sleep(2)
        
        # Verify election results
        vote_count = 1  # Candidate votes for itself
        for node in self.nodes[1:]:
            if node.voted_for == candidate_node.node_id:
                vote_count += 1
        
        # Check if candidate became leader (needs majority)
        if vote_count > len(self.nodes) // 2:
            self.assertEqual(candidate_node.state, "leader")
            logging.info(f"Node {candidate_node.node_id} became leader with {vote_count} votes")
        else:
            self.assertNotEqual(candidate_node.state, "leader")
            logging.info(f"Node {candidate_node.node_id} failed to become leader. Got {vote_count} votes")

    def test_log_replication(self):
        """Test log replication and database storage"""
        # Wait for leader election
        time.sleep(5)
        
        # Find leader
        leader = None
        for node in self.nodes:
            if node.state == "leader":
                leader = node
                break
        
        self.assertIsNotNone(leader, "No leader found")
        
        # Create test entry
        test_entry = {
            "term": leader.current_term,
            "command": "test_command",
            "timestamp": int(time.time()),
            "index": len(leader.log)
        }
        
        # Append entry and write to database
        leader.append_entry(test_entry)
        
        # Wait for replication
        time.sleep(2)
        
        # Verify in MongoDB
        client = pymongo.MongoClient(self.db_uri)
        db = client[self.db_name]
        collection = db[self.db_collection]
        
        # Check database entries
        db_entries = list(collection.find({"command": "test_command"}))
        self.assertEqual(len(db_entries), 1, "Log entry not found in database")
        
        # Check if all nodes have the entry
        for node in self.nodes:
            self.assertEqual(len(node.log), 1, f"Node {node.node_id} did not replicate the log")
            
        client.close()

    def test_status_query(self):
        """Test status query functionality and database storage"""
        # Create status collection
        client = pymongo.MongoClient(self.db_uri)
        db = client[self.db_name]
        status_collection = db['node_status']
        status_collection.delete_many({})  # Clear previous status
        
        for i, node in enumerate(self.nodes):
            # Get node status
            status = node.Status(raft_pb2.StatusRequest(), None)
            self.assertIsNotNone(status)
            self.assertEqual(status.log_count, len(node.log))
            
            # Store status in MongoDB
            status_doc = {
                "node_id": node.node_id,
                "state": status.state,
                "current_term": status.current_term,
                "log_count": status.log_count,
                "timestamp": int(time.time())
            }
            status_collection.insert_one(status_doc)
        
        # Verify status storage
        stored_status = list(status_collection.find())
        self.assertEqual(len(stored_status), len(self.nodes), 
                        "Not all node statuses were stored in database")
        
        client.close()

if __name__ == '__main__':
    unittest.main()