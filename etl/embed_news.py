import json
import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

def main():
    print("初始化本地Embedding模型(首次运行会下载约90MB的模型)")
    ef = SentenceTransformerEmbeddingFunction(model_name = "all-MiniLM-L6-v2")

    #确保保存数据库的目录存在
    os.makedirs("./data/chroma", exist_ok=True)

    print("链接本地ChromaDB...")
    client = chromadb.PersistentClient(path="./data/chroma")
    collection = client.get_or_create_collection(name = "news", embedding_function=ef)

    news = []

    #读取真实新闻
    try:
        with open("data/raw/news.json", "r", encoding='utf-8') as f:
            news.extend(json.load(f))
    except FileNotFoundError:
        print("！警告！未找到news文件")

    #读取保底mock新闻
    try:
        with open("data/raw/news_manual.json", "r", encoding='utf-8') as f:
            news.extend(json.load(f))
    except FileNotFoundError:
        print("！警告！未找到new manual文件")

    if not news:
        print("错误 没有新闻数据可供向量化，请确保前序步骤")
        return
    
    # 提取数据，写入chromaDB
    documents = [n.get("title", "") for n in news]
    metadatas = [{"date": n.get("date", ""), "tickers":n.get("tickers", "")} for n in news]
    ids = [f"news_{i}" for i in range(len(news))]

    print(f"正在将{len(news)}条数据 写入ChromaDB")

    # 使用upsert代替add。如果多次运行脚本，相同id会更新，不会报错
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids = ids
    )
    print("成功将新闻向量化 并写入本地ChromaDB!")

if __name__ == "__main__":
    main()