import asyncio
import json
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import app as agent_app

app = FastAPI(title="MarketTruth Agent API")

class AttributionRequest(BaseModel):
    ticker: str
    target_date: str

async def generate_sse_stream(request: Request, ticker:str, target_date:str):
    """
    核心流式生成器：监听Agent运行时的所有细粒度事件，并包装为SSE格式
    """
    req_id = str(uuid.uuid4())
    # 1. 构造初始State
    initial_state = {
        "messages": [
            HumanMessage(content=f"请调查{ticker}在{target_date}的股价异动原因")
        ],
        "step_count": 0,
        "evidence_pool": [],
        "visited_entities": [],
        "request_id": req_id
    }

    try:
        # 2.调用 astream_events (v2时目前LangChain推荐的事件流版本)
        async for event in agent_app.astream_events(initial_state, version="v2"):
            if await request.is_disconneted():
                print(f"[SSE] Client disconnected for request{req_id}. Terminating stream.")
                break

            kind = event["event"]
            # 获取当前事件发生在哪个节点
            node_name = event.get("metadata", {}).get("langgraph_node", "")

            # 补丁：拦截 Planner 的决定，精准推送工具调用状态
            # 替代 on_tool_start，因为我们覆写了 action_node 且没传 config
            if kind == "on_chat_model_end" and node_name == "planner":
                output_msg = event.get("data", {}).get("output", {})
                if isinstance(output_msg, AIMessage) and output_msg.tool_calls:
                    for tc in output_msg.tool_calls:
                        msg = json.dumps({
                            "type": "thought",
                            "content": f"🔍 正在调用工具 [{tc['name']}] 进行探勘... 参数: {tc['args']}"
                        }, ensure_ascii=False)
                        yield f"data: {msg}\n\n"

            
            # 场景B:捕获Reporter节点的LLM流式输出(打字机效果)
            # 必须过滤 node_name == "reporter", 否则思考时隐藏token会漏出
            elif kind == "on_chat_model_stream" and node_name =="reporter":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    #兼容部分大模型返回的内容不是字符串
                    content_str = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    msg = json.dumps({"type": "token","content": content_str},ensure_ascii=False)
                    yield f"data: {msg}\n\n"
            
            elif kind == "on_chain_end" and event["name"] == "LangGraph":
                msg = json.dumps({"type": "done", "content": "\n\n 分析结束。"}, ensure_ascii=False)
                yield f"data: {msg}\n\n"
            
            # 插入隐形心跳，防止 Nginx / 浏览器 掐断长连接
            yield ": keep-alive\n\n"
    except Exception as e:
        error_msg = json.dumps({
            "type": "error",
            "content": f"\n\n❌ 系统执行异常: {str(e)}"
        }, ensure_ascii=False)
        yield f"data: {error_msg}\n\n"
        print(f"[SSE Error] Request {req_id} failed: {e}")

@app.post("/api/v1/analyze")
async def analyze_stock_anomaly(payload: AttributionRequest, request: Request):
    """
    对外暴露的SSE流式接口
    """
    return StreamingResponse(
        generate_sse_stream(request, payload.ticker, payload.target_date),
        media_type="text/event-stream",
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # 极其关键：防止 Nginx 缓存流式响应
        }
    )

if __name__ == "__main__":
    print(" 启动 Market Truth Agent 服务...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)