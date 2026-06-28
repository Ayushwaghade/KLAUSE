import os
from pymongo import MongoClient
from loguru import logger
from app.config.config import settings

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []
    def insert_one(self, doc):
        doc["_id"] = str(len(self.docs) + 1)
        self.docs.append(doc)
        return type("InsertResult", (object,), {"inserted_id": doc["_id"]})()
    def find(self, filter_query=None):
        results = list(self.docs)
        if filter_query and "session_id" in filter_query:
            results = [d for d in results if d.get("session_id") == filter_query["session_id"]]
        return MockCursor(results)
    def update_one(self, filter_query, update_data, upsert=False):
        pass

class MockCursor:
    def __init__(self, docs):
        self.docs = docs
    def sort(self, key, direction=1):
        if isinstance(key, list):
            reverse_sort = (key[0][1] == -1)
        else:
            reverse_sort = (direction == -1)
            
        if self.docs:
            import datetime
            self.docs.sort(
                key=lambda x: (x.get("timestamp") or datetime.datetime.min, str(x.get("_id", ""))),
                reverse=reverse_sort
            )
        return self
    def limit(self, count):
        self.docs = self.docs[:count]
        return self
    def __iter__(self):
        return iter(self.docs)

class MockDatabase:
    def __init__(self):
        self.conversations = MockCollection("conversations")
        self.notes = MockCollection("notes")
        self.research = MockCollection("research")
        self.projects = MockCollection("projects")
        self.tasks = MockCollection("tasks")

class MongoDBClient:
    def __init__(self):
        self.uri = settings.mongo_uri or settings.memory.mongo_uri
        self.db_name = settings.mongo_db or settings.memory.mongo_db
        self.client = None
        self.db = None
        self.is_connected = False
        
        logger.info(f"Connecting to MongoDB URI: {self.uri}")
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=2000)
            self.db = self.client[self.db_name]
            # Verify connection
            self.client.server_info()
            self.is_connected = True
            logger.info(f"Successfully connected to MongoDB database: {self.db_name}")
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}. Falling back to In-Memory mock database.")
            self.db = MockDatabase()

    def get_db(self):
        return self.db

# Global MongoDB Client instance
_mongo_client_inst = None

def get_db():
    global _mongo_client_inst
    if _mongo_client_inst is None:
        _mongo_client_inst = MongoDBClient()
    return _mongo_client_inst.get_db()
