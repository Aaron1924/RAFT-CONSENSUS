import pymongo
import time
import threading
import logging
import uuid
import raft_pb2

# Configure logging (important!)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Database:
    def __init__(self, uri, db_name, collection_name):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.lock = threading.Lock()  # Add a lock for thread safety

        # Create index if it doesn't exist (crucial for performance)
        try:
            self.collection.create_index([("index", pymongo.ASCENDING)])
        except pymongo.errors.PyMongoError as e:
            logging.error(f"Error creating index: {e}")

    def append_entry(self, entry):
        """Append a log entry to the database."""
        with self.lock:  # Acquire the lock before any database operation
            max_retries = 5
            retry_delay = 1
            for attempt in range(max_retries):
                try:
                    # Ensure a unique ID is generated for the entry
                    entry['_id'] = str(uuid.uuid4())
                    result = self.collection.insert_one(entry)  # Use insert_one to add the document
                    logging.info(f"Successfully inserted log entry: {entry}")
                    break
                except pymongo.errors.PyMongoError as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Database insert failed after multiple retries: {e}")
                        raise  # Re-raise the exception if all retries fail
                    else:
                        logging.warning(f"Database insert failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2

    def get_entry(self, index):
        """Retrieve a log entry based on its index."""
        with self.lock:
            try:
                entry = self.collection.find_one({"index": index})
                if entry:
                    # Decode the command to return a structured LogEntry object
                    log_entry = raft_pb2.LogEntry(
                        term=entry['term'],
                        command=entry['command'].encode(),  # Convert command to bytes
                        timestamp=entry['timestamp']
                    )
                    logging.info(f"Retrieved log entry: {log_entry}")
                    return log_entry
                logging.warning(f"No entry found for index: {index}")
                return None
            except Exception as e:
                logging.error(f"Error retrieving entry: {e}")
                return None

    def close(self):
        """Close the database connection."""
        self.client.close()
        logging.info("Database connection closed.")