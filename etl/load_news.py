from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf

# 配置
RAW_DIR = Path("data/raw")
TICKERS = ["AAPL", "TSM"]

def _date_from_any(item: dict) -> str | None:
    """
    兼容 yfinance.news 两种常见格式：
    1) 顶层 providerPublishTime (unix seconds)
    2) item["content"]["pubDate"] / ["displayTime"] (ISO string, e.g. 2026-03-02T11:53:00Z)
    返回 YYYY-MM-DD（UTC）
    """
    # 1) providerPublishTIme (unix seconds)
    ts = item.get("providerPublishTime")
    if ts is not None:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            pass

    # 2) ISO String in content
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    iso = content.get("pubDate") or content.get("displayTime")
    if iso:
        try:
            # example: 2026-02-27T19:05:00Z
            # 'Z' -> '+00:00' 才能被 fromisoformat 正确解析
            # 其实3.12已经可以了 不需要替换Z
            iso2 = iso.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso2)
            # 保证UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return None
            
    return None

def _normalize_related_tickers(value: Any, fallback: str) -> list[str]:
    """relatedTickers 可能是list/str/None, 统一成list[str]"""
    if not value:
        return [fallback]
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out = [x for x in value if isinstance(x, str) and x.strip()]
        return out if out else [fallback]
    return [fallback]

def get_market_news() -> list[dict]:
    """获取新闻并标准化处理：去重、UTC时间、字段校验"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_news: list[dict] = []
    seen: set[str] = set()

    for t in TICKERS:
        print(f" 正在拉取{t}相关新闻...")
        news_items = yf.Ticker(t).news or []
        print(f"[debug] {t} raw news count={len(news_items)}")

        for item in news_items:
            content = item.get("content") if isinstance(item.get("content"), dict) else item
            title = (content.get("title") or item.get("title") or "").strip()
            link = (
                (content.get("canonicalUrl") or {}).get("url")
                or (content.get("clickThroughUrl") or {}).get("url")
                or item.get("link")
                or content.get("link")
                or None
            )
            dt_str = _date_from_any(item)
            if not dt_str:
                print("没有publishTime 跳过")
                continue
            
            # 去重 link > title
            key = (str(link).strip() if link else "") or title
            if not key or key in seen:
                continue
            seen.add(key)

            related = _normalize_related_tickers(item.get("relatedTickers"), fallback=t)

            publisher = None
            provider = content.get("provider")
            if isinstance(provider, dict):
                publisher = provider.get("displayName")
            publisher = publisher or content.get("publisher") or item.get("publisher") or item.get("provider")

            all_news.append(
                {
                    "date": dt_str,
                    "ticker": t,
                    "relatedTickers": related,
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                }
            )
    return all_news
    
def main():
    # 这里是覆盖重写，不是增量抓取
    # TODO 改成增量抓取
    try:
        news_data = get_market_news()
        out_path = RAW_DIR / "news.json"
        with open(out_path, 'w', encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)

        print(f"\n ok 成功抓取并去重，共{len(news_data)}条新闻")
        if news_data:
            s = news_data[0]
            print(f"采样数据：[{s['date']}] {s['ticker']} == {(s['title'] or  "")[:25]}...")

    except Exception as e:
        print(f"load_news ETL运行失败: {e}")
    
if __name__ == "__main__":
    main()