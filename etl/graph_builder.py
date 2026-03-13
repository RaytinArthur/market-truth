import hashlib
import logging
import re

from tqdm import tqdm

from utils.error_logger import log_error, ErrorType

class GraphBuilder:
    def __init__(self, driver, normalizer):
        self.driver = driver
        self.normalizer = normalizer
    
    def gen_news_id(self, news_item:dict) -> str:
        raw = f"{news_item.get('date', '')}|{news_item.get('title', '')}|{news_item.get('publisher', '')}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def extract_mentions(self, news_item:dict) -> list[str]:
        candidates = []
        if news_item.get("ticker"):
            candidates.append(news_item["ticker"])
        
        # 下面return的时候 去重了
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
            else:
                # --- 新增：实体对齐失败埋点 ---
                log_error(
                    error_type=ErrorType.ENTITY_ALIGNMENT_FAILURE,
                    query=c,             # 记录解析失败的原始字符串
                    context=title,       # 把新闻标题作为上下文留存，方便溯源
                    details={
                        "news_url": news_item.get("link", ""),
                        "step": "normalizer.normalize"
                    }
                )
        
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
        news_id = self.gen_news_id(news_item)
        tickers = self.extract_mentions(news_item)
        themes = self.classify_themes(news_item)

        query = """
        MERGE (n:News {news_id: $news_id})
        SET n.title = $title,
            n.content = $content,
            n.date = $date,
            n.publisher = $publisher,
            n.url = $url

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
            "news_id": news_id,
            "title": news_item.get("title", ""),
            "content": news_item.get("content", ""),
            "date": news_item.get("date", ""),
            "publisher": news_item.get("publisher", ""),
            "url": news_item.get("link", ""),
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
                logging.error("Failed to process news: %s", e)

    def ensure_constraints(self) -> None:
        queries = [
            "CREATE CONSTRAINT company_ticker_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
            "CREATE CONSTRAINT news_id_unique IF NOT EXISTS FOR (n:News) REQUIRE n.news_id IS UNIQUE",
            "CREATE CONSTRAINT theme_name_unique IF NOT EXISTS FOR (t:Theme) REQUIRE t.name IS UNIQUE",
        ]
        with self.driver.session() as session:
            for q in queries:
                session.run(q)