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
        self.commit_index = 0 # Add commitIndex tracking in the Database
        self.kvstore_collection = self.db["kvstore"] # For key-value store
        self.kvstore_lock = threading.Lock() # Lock for key-value operations

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
                    entry['index'] = self.get_last_log_index() + 1 # set by Database
                    result = self.collection.insert_one(entry)
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
                        
    def get_last_log_index(self):
        """Get the index of the last log entry."""
        with self.lock:
            try:
                last_entry = self.collection.find().sort("index", pymongo.DESCENDING).limit(1)[0]
                return last_entry.get('index', 0)  # Return 0 if no entries
            except IndexError: #  handle empty collection
                return 0
            except Exception as e:
                logging.error(f"Error getting last log index: {e}")
                return 0

    def get_entries_from_index(self, start_index):
        """Retrieve log entries starting from a given index."""
        with self.lock:
            try:
                entries = list(self.collection.find({"index": {"$gte": start_index}}).sort("index", pymongo.ASCENDING))
                log_entries = []
                for entry in entries:
                    log_entry = raft_pb2.LogEntry(
                        term=entry['term'],
                        command=entry['command'].encode(),
                        timestamp=entry['timestamp']
                    )
                    log_entries.append(log_entry)

                return log_entries

            except Exception as e:
                logging.error(f"Error retrieving entries from index: {e}")
                return []


    def apply_committed_entries(self):
        """Apply committed log entries to the key-value store."""
        with self.lock, self.kvstore_lock:  # Acquire both locks to prevent race conditions
            while self.last_applied < self.commit_index:
                log_entry = self.get_entry(self.last_applied+1)
                if log_entry:
                    try:
                        command = log_entry.command.decode().split()  # Split command into parts
                        if command[0] == "set":  # set key value
                            key, value = command[1], command[2]
                            self.kvstore_collection.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
                        elif command[0] == "get":  # Implement 'get' functionality if needed
                            pass  # Add 'get' logic here if needed
                        self.last_applied += 1
                        logging.info(f"Applied entry at index {log_entry.index}, lastApplied: {self.last_applied}, commitIndex: {self.commit_index}")
                    except Exception as e:
                        logging.error(f"Error applying log entry: {e}") # Handle any errors during command application
                        break
                else:
                    logging.warning(f"No log entry found for index {self.last_applied + 1}.")
                    break

    def set_commit_index(self, commit_index):
        with self.lock:
            if commit_index > self.commit_index:
                self.commit_index = min(commit_index, self.get_last_log_index())  # Ensure commitIndex doesn't exceed log index
                self.apply_committed_entries() # apply the logs after updating commitIndex


    def get_value(self, key):
        with self.kvstore_lock:  # Acquire the lock before accessing the kvstore
            result = self.kvstore_collection.find_one({"key": key})
            return result["value"] if result else None

    def close(self):
       """Close the database connection."""
       self.client.close()
       logging.info("Database connection closed.")