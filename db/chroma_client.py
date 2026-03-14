import os
import chromadb

from config import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME

class ChromaClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'client'):
            self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    def get_collection(self, collection_name = CHROMA_COLLECTION_NAME):
        return self.client.get_or_create_collection(name=collection_name)