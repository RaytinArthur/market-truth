from neo4j import GraphDatabase

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from retriever.graph_retriever import GraphRetriever

driver = GraphDatabase.driver(
        NEO4J_URI,
        auth = (NEO4J_USER, NEO4J_PASSWORD)
        )

retriever = GraphRetriever(driver)

results = retriever.retrieve(
    ticker= "AAPL",
    target_date="2024-08-01"
)

for r in results:
    print(r)