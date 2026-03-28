from datetime import datetime, timedelta
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import EMBEDDING_MODEL_NAME, CHROMA_COLLECTION_NAME
from db.chroma_client import ChromaClient

class VectorRetriever:
    def __init__(self):
        # 从解耦的DB层获取client,并再次绑定Embedding函数
        client = ChromaClient().client
        ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)
        self.collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=ef
        )


    def _safe_parse_date(self, date_str: str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None

    def _format_results(self, results: dict) -> list[dict]:
        """
        将 Chroma 原始查询结果格式化为结构化新闻列表
        """
        if not results or not results.get("documents"):
            return []

        documents = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        news_list = []
        for i in range(len(documents)):
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else None

            news_list.append(
                {
                    "title": documents[i],
                    "date": metadata.get("date", ""),
                    "ticker": metadata.get("ticker", ""),
                    "related_tickers": metadata.get("related_tickers", ""),
                    "publisher": metadata.get("publisher", ""),
                    "link": metadata.get("link", ""),
                    "distance": distance,
                }
            )

        return news_list

    def search_news(self, query: str, top_k: int = 3) -> list[dict]:
        """
        根据 query 做全局语义检索
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        return self._format_results(results)

    def search_news_by_ticker(self, query: str, ticker: str, top_k: int = 3) -> list[dict]:
        """
        根据 query + ticker 检索相关新闻
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"ticker": ticker},
        )
        return self._format_results(results)

    def search_news_by_ticker_and_date(
            self,
            query: str,
            ticker: str,
            target_date: str,
            top_k: int = 3,
            candidate_num : int = 8,
            max_days_before: int = 30,
    ) -> list[dict]:
        """
        避免 look-ahead bias
        只查询 target_date 及之前 max_days_before 天内的新闻，再按距离重排
        """
        target = self._safe_parse_date(target_date)
        # 如果目标日期解析失败，降级为纯 ticker 检索兜底
        if target is None:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"ticker": ticker},
            )
            return self._format_results(results)

        # 计算安全的时间窗口：[target - 30天, target]
        start_date = target - timedelta(days=max_days_before)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = target.strftime("%Y-%m-%d")

        # ChromaDB 魔法：元数据下推过滤 (Pre-filtering)
        # 彻底解决 Python 内存里的“漏斗截断”问题
        results = self.collection.query(
            query_texts=[query],
            n_results=candidate_num,
            where={
                "$and": [
                    {"ticker": {"$eq": ticker}},
                    {"date": {"$gte": start_str}}, 
                    {"date": {"$lte": end_str}}
                ]
            }
        )

        news_list = self._format_results(results)

        # 此时查出来的结果一定在时间窗口内，且绝对没有“未来数据”
        # 我们只需要计算时间差，并做个精细排序即可
        for news in news_list:
            news_date = self._safe_parse_date(news.get("date", ""))
            if news_date:
                news["date_distance"] = abs((target - news_date).days)
            else:
                news["date_distance"] = float('inf')

        # 排序策略：
        # 1. 日期更近优先
        # 2. 语义距离更小优先（distance 越小越相似）
        news_list.sort(
            key=lambda x: (
                x.get("date_distance", float('inf')),
                x.get("distance", float('inf')) if x.get("distance") is not None else float('inf'),
            )
        )

        return news_list[:top_k]

if __name__ == "__main__":
    print("开始验证语义搜索")
    retriver = VectorRetriever()
    # test case 1 测试Apple抛售新闻
    query1 = "Big investor dumping Apple stock"
    print(f" 查询 1 ： {query1}")
    print("🎯 期望: 命中巴菲特/伯克希尔抛售苹果的相关新闻")
    results1 = retriver.search_news(query1)
    for i, item in enumerate(results1, 1):
        print(f"[{i}] {item['title']}")
        print(f"date={item['date']}, ticker={item['ticker']}, publisher={item['publisher']}")
    print("-*" * 15)

    # test case 2 测试供应链与芯片
    query2 = "Smartphone chip and iPhone production issues"
    print(f" 查询 2： {query2}")
    print("🎯 期望: 命中 TSMC 芯片需求或 iPhone 16 供应链订单调整的新闻")
    results2 = retriver.search_news(query2)
    for i, item in enumerate(results2, 1):
        print(f"[{i}] {item['title']}")
        print(f"date={item['date']}, ticker={item['ticker']}, publisher={item['publisher']}")