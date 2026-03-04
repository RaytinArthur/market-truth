import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# 初始化 与 写入时完全相同的 Embedding模型 和 Chroma 客户端
ef = SentenceTransformerEmbeddingFunction(model_name = "all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./data/chroma")
collection = client.get_or_create_collection(name="news", embedding_function=ef)

def search_news(query:str, top_k: int = 3):
    """
    根据query检索最相关新闻
    """
    results = collection.query(
        query_texts = [query],
        n_results=top_k
    )

    if results and "documents" in results and results["documents"]:
        return results["documents"][0]
    return []

if __name__ == "__main__":
    print("开始验证语义搜索")

    # test case 1 测试Apple抛售新闻
    query1 = "Big investor dumping Apple stock"
    print(f" 查询 1 ： {query1}")
    print("🎯 期望: 命中巴菲特/伯克希尔抛售苹果的相关新闻")
    results1 = search_news(query1)
    for i, title in enumerate(results1, 1):
        print(f"[{1}, {title}]")
    print ("-*" * 15)

    # test case 2 测试供应链与芯片
    query2 = "Smartphone chip and iPhone production issues"
    print(f" 查询 2： {query2}")
    print("🎯 期望: 命中 TSMC 芯片需求或 iPhone 16 供应链订单调整的新闻")
    results2 = search_news(query2)
    for i, title in enumerate(results2, 1):
        print(f"[{1}, {title}]")
