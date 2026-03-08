import json
import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    RAW_DATA_DIR,
)

def main():
    print("初始化本地Embedding模型(首次运行会下载约90MB的模型)")
    ef = SentenceTransformerEmbeddingFunction(model_name = EMBEDDING_MODEL_NAME)

    #确保保存数据库的目录存在
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)

    print("链接本地ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name = CHROMA_COLLECTION_NAME, embedding_function=ef)

    news = []

    #读取真实新闻 和 保底新闻
    for filename in ["news.json", "news_manual.json"]:
        try:
            with open(f"{RAW_DATA_DIR}/{filename}", "r", encoding="utf-8") as f:
                news.extend(json.load(f))
        except FileNotFoundError:
            print(f"警告：未找到 {filename}")

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