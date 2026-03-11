import json
from neo4j import GraphDatabase

from config import NEO4J_URI,NEO4J_USER,NEO4J_PASSWORD
from etl.graph_builder import GraphBuilder
from etl.normalizer import EntityNormalizer

def main():
    news_list = []
    for path in [
        "data/raw/news.json",
        "data/raw/news_manual.json",
    ]:
        with open(path, "r", encoding="utf-8") as f:
            news_list.extend(json.load(f))

        driver = GraphDatabase.driver(
        NEO4J_URI,
        auth = (NEO4J_USER, NEO4J_PASSWORD)
        )
        
        normalizer = EntityNormalizer()
        builder = GraphBuilder(driver, normalizer)

        builder.ensure_constraints()
        builder.batch_process(news_list)

        driver.close()

if __name__ == "__main__":
    main()