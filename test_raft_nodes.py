import unittest
import time
import grpc
import pymongo
import random
from dotenv import load_dotenv
import os
import raft_pb2
import raft_pb2_grpc
from raft_node import Node
import threading
import logging
import futures


class TestRaftNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        # Node configuration
        cls.base_port = 5000
        cls.num_nodes = 5
        cls.peers = [f'localhost:{cls.base_port + i}' for i in range(cls.num_nodes)]
        
        # Load environment variables
        load_dotenv()
        
        # MongoDB configuration
        cls.db_uri = "mongodb://localhost:27017"
        cls.db_name = "raft_test"
        cls.db_collection = "test_logs"
        
        # Clear test database
        client = pymongo.MongoClient(cls.db_uri)
        for i in range(cls.num_nodes):
            node_db_name = f"{cls.db_name}_node_{i}"
            client.drop_database(node_db_name)
        client.close()
        

    def setUp(self):
        self.nodes = []
        self.servers = []  # List to store gRPC servers
        self.node_threads = []

        for i in range(self.num_nodes):
            port = self.base_port + i  # Unique port for each node
            node = Node(
                node_id=i,
                db_uri=self.db_uri,
                db_name=f"{self.db_name}_node_{i}",  # Unique db name per node!
                db_collection=self.db_collection
            )
            node.peers = [f'localhost:{self.base_port + j}' for j in range(self.num_nodes)]
            self.nodes.append(node)

            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))  # Create the gRPC server
            raft_pb2_grpc.add_RaftServiceServicer_to_server(node, server)
            server.add_insecure_port(f'[::]:{port}')
            self.servers.append(server) # Store the server

            thread = threading.Thread(target=self._run_node, args=(node, server, port,))  # Correct thread target
            thread.daemon = True # daemon true to close thread with main process
            thread.start()
            self.node_threads.append(thread)


        time.sleep(0.5)  # Allow time for nodes to start

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

    
    
    
    def test_leader_election(self):
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
    
    
    def test_candidate_wins_election(self):
        # Force a leader
        leader_node = self.nodes[0]
        leader_node.become_leader(leader_node.current_term)  # Ensure initial leader for testing
        time.sleep(0.5)  # Allow time for stabilization
        self.assertEqual("leader", leader_node.state)

        # Isolate leader
        for node in self.nodes:
            if node != leader_node:
                node.peers = []  # Temporarily isolate node

        # Now force election on a specific candidate
        candidate_node = self.nodes[1]

        candidate_node.start_election()
        time.sleep(0.5)  # Allow election time

        self.assertEqual("leader", candidate_node.state, f"Node {candidate_node.node_id} should be leader")

        # Reset Peers to original state (important for other tests):
        for i, node in enumerate(self.nodes):
            node.peers = [f'localhost:{self.base_port + j}' for j in range(self.num_nodes)]

    def test_no_split_vote(self):
        """Tests that there cannot be more than 1 leader in a term"""

        # Force multiple nodes to start elections
        for node in self.nodes:
            node.reset_election_timer() # Reset to start elections


        time.sleep(1)  # Wait for elections to complete (adjust as needed)

        leaders = [node for node in self.nodes if node.state == "leader"]
        self.assertLessEqual(len(leaders), 1, "There should be at most one leader per term")  # Assert at most one leader




    def test_follower_rejects_stale_vote_request(self):
        """Test that followers reject stale term RequestVote RPCs."""
        follower = self.nodes[1]
        candidate = self.nodes[0]

        with follower.lock, candidate.lock:  # Protect term and voted_for with locks
            follower.current_term = 2
            candidate.current_term = 1

            request = raft_pb2.RequestVoteRequest(
                term=candidate.current_term,
                candidateId=candidate.node_id,
                lastLogIndex=0,
                lastLogTerm=0
            )
            response = follower.RequestVote(request, None)

        self.assertFalse(response.voteGranted, "Vote should not be granted for a stale term")


    def test_higher_term_forces_follower(self):

        leader = self.nodes[0]
        follower = self.nodes[1]
        with leader.lock, follower.lock:
             leader.state = 'leader'
             leader.current_term = 1
             follower.current_term = 2


             request = raft_pb2.AppendEntriesRequest(term=follower.current_term, leaderId =follower.node_id, prevLogIndex=0, prevLogTerm=0, entries=[], leaderCommit=0 )
             response = leader.AppendEntries(request, None)

        self.assertEqual(leader.state, 'follower')


    def test_election_timeout_variability(self):
        """Servers have different election timeouts, shortest wins."""
        timeouts = [random.uniform(0.15, 0.3) for _ in self.nodes]  # Different timeouts
        for i, node in enumerate(self.nodes):
            node.election_timeout = timeouts[i]
        
        # Find minimum Timeout Index to determine expected winner
        min_timeout = min(timeouts)

        for i, node in enumerate(self.nodes):
            node.start_election()

        time.sleep(min_timeout + 0.1)  # let the fastest candidate win



        leaders = [node for node in self.nodes if node.state == "leader"]
        if any(leaders):
            self.assertEqual(len(leaders), 1)
            leader = leaders[0]
    

    # def test_log_replication(self):
    #     """Test log replication and database storage"""
    #     # Wait for leader election
    #     time.sleep(5)
        
    #     # Find leader
    #     leader = None
    #     for node in self.nodes:
    #         if node.state == "leader":
    #             leader = node
    #             break
        
    #     self.assertIsNotNone(leader, "No leader found")
        
    #     # Create test entry
    #     test_entry = {
    #         "term": leader.current_term,
    #         "command": "test_command",
    #         "timestamp": int(time.time()),
    #         "index": len(leader.log)
    #     }
        
    #     # Append entry and write to database
    #     leader.append_entry(test_entry)
        
    #     # Wait for replication
    #     time.sleep(2)
        
    #     # Verify in MongoDB
    #     client = pymongo.MongoClient(self.db_uri)
    #     db = client[self.db_name]
    #     collection = db[self.db_collection]
        
    #     # Check database entries
    #     db_entries = list(collection.find({"command": "test_command"}))
    #     self.assertEqual(len(db_entries), 1, "Log entry not found in database")
        
    #     # Check if all nodes have the entry
    #     for node in self.nodes:
    #         self.assertEqual(len(node.log), 1, f"Node {node.node_id} did not replicate the log")
            
    #     client.close()

    # def test_status_query(self):
    #     """Test status query functionality and database storage"""
    #     # Create status collection
    #     client = pymongo.MongoClient(self.db_uri)
    #     db = client[self.db_name]
    #     status_collection = db['node_status']
    #     status_collection.delete_many({})  # Clear previous status
        
    #     for i, node in enumerate(self.nodes):
    #         # Get node status
    #         status = node.Status(raft_pb2.StatusRequest(), None)
    #         self.assertIsNotNone(status)
    #         self.assertEqual(status.log_count, len(node.log))
            
    #         # Store status in MongoDB
    #         status_doc = {
    #             "node_id": node.node_id,
    #             "state": status.state,
    #             "current_term": status.current_term,
    #             "log_count": status.log_count,
    #             "timestamp": int(time.time())
    #         }
    #         status_collection.insert_one(status_doc)
        
    #     # Verify status storage
    #     stored_status = list(status_collection.find())
    #     self.assertEqual(len(stored_status), len(self.nodes), 
    #                     "Not all node statuses were stored in database")
        
    #     client.close()

if __name__ == '__main__':
    unittest.main()