import json
from neo4j import GraphDatabase

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from etl.normalizer import EntityNormalizer
from etl.graph_builder import GraphBuilder

def main():
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth = (NEO4J_USER, NEO4J_PASSWORD)
    )

    normalizer = EntityNormalizer()
    builder = GraphBuilder(driver, normalizer)

    sample_news = {
        "id": "test-1",
        "ticker": "AAPL",
        "relatedTickers": ["TSM"],
        "title": "Apple shares fall as weak demand hits suppliers",
        "content": "Taiwan Semiconductor may face lower orders after softer iPhone demand.",
        "date": "2024-08-02"
    }

    try:
        print("=== Python logic test ===")
        print("mentions:", builder.extract_mentions(sample_news))
        print("themes:", builder.classify_themes(sample_news))

        print("\n=== Neo4j write test ===")
        builder.write_news_to_graph(sample_news)
        print("single news written successfully")
    finally:
        driver.close()

if __name__ == "__main__":
    main()