import pymongo

def test_connection():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client.raft
    print("MongoDB connection successful")
    print(f"Database names: {client.list_database_names()}")

if __name__ == "__main__":
    test_connection()