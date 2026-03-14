from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class Neo4jClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 防抖：确保 driver 只被创建一次
        if not hasattr(self, 'driver'):
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def get_driver(self):
        return self.driver
    
    def close(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()