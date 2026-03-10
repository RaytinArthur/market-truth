import logging
import re

from tqdm import tqdm

class GraphBuilder:
    def __init__(self, driver, normalizer):
        self.driver = driver
        self.normalizer = normalizer

    def extract_mentions(self, news_item:dict) -> list[str]:
        candidates = []
        if news_item.get("ticker"):
            candidates.append(news_item["ticker"])
        
        if isinstance(news_item.get("relatedTickers"), list):
            candidates.extend(news_item["relatedTickers"])
        
        title = news_item.get("title", "")
        content = news_item.get("content", "")
        full_text = f"{title} {content}".lower()

        for alias in self.normalizer.alias_map.keys():
            if re.search(rf"\b{re.escape(alias)}\b", full_text):
                candidates.append(alias)
        
        tickers = []
        for c in candidates:
            t = self.normalizer.normalize(c)
            if t:
                tickers.append(t)
        
        return sorted(set(tickers))
    
    def classify_themes(self, news_item:dict) -> list[str]:
        text = f"{news_item.get('title', '')} {news_item.get('content', '')}".lower()
        themes = []

        if any(k in text for k in  ["cut stake", "reduced stake", "sell-off", "trimmed stake"]):
            themes.append("StakeReduction")

        if any(k in text for k in ["slow demand", "weak demand", "soft sales", "orders cut"]):
            themes.append("DemandSlowdown")

        if any(k in text for k in ["supply chain", "supplier", "production delay", "shortage"]):
            themes.append("SupplyChainRisk")

        if any(k in text for k in ["downgrade", "rating cut", "cut to hold", "cut to neutral"]):
            themes.append("AnalystDowngrade")

        if any(k in text for k in ["inflation", "fed", "interest rates", "recession", "macro"]):
            themes.append("MacroRisk")

        return themes if themes else ["Other"]
    
    def write_news_to_graph(self, news_item: dict) -> None:
        tickers = self.extract_mentions(news_item)
        themes = self.classify_themes(news_item)

        query = """
        MERGE (n:News {news_id: $news_id})
        SET n.title = $title,
            n.content = $content,
            n.date = $date

        WITH n
        UNWIND $tickers AS ticker
        MERGE (c:Company {ticker: ticker})
        MERGE (n)-[:MENTIONS]->(c)

        WITH DISTINCT n
        UNWIND $themes AS theme_name
        MERGE (t:Theme {name: theme_name})
        MERGE (n)-[:HAS_THEME]->(t)
        """

        params = {
            "news_id": str(news_item["id"]),
            "title": news_item.get("title", ""),
            "content": news_item.get("content", ""),
            "date": news_item.get("date", ""),
            "tickers": tickers,
            "themes": themes,
        }

        with self.driver.session() as session:
            session.run(query, params)

    def batch_process(self, news_list: list[dict])-> None:
        for item in tqdm(news_list, desc="Ingesting News"):
            try:
                self.write_news_to_graph(item)
            except Exception as e:
                logging.error("Failed to process news_id=%s:%s", item.get("id"), e)