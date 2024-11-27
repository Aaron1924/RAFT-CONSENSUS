# test_node_status.py
import grpc
import raft_pb2
import raft_pb2_grpc
import unittest

class TestNodeStatus(unittest.TestCase):
    def setUp(self):
        self.channel = grpc.insecure_channel('localhost:5000')
        self.stub = raft_pb2_grpc.RaftServiceStub(self.channel)

    def test_node_status(self):
        request = raft_pb2.StatusRequest(node_id=0)
        try:
            response = self.stub.Status(request)
            print(f"Node state: {response.state}")
            print(f"Current term: {response.current_term}")
            print(f"Log count: {response.log_count}")
            print(f"Is leader: {response.is_leader}")
        except grpc.RpcError as e:
            print(f"Error connecting to node: {e}")

if __name__ == '__main__':
    unittest.main()