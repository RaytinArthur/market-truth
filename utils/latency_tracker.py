import time
from contextvars import ContextVar

# 核心：天生为异步和并发设计的上下文隔离容器
_latency_ctx: ContextVar[dict] = ContextVar("latency_ctx")

class LatencyTracker:
    @classmethod
    def initialize(cls):
        """在请求的最外层（如 FastAPI Middleware, 或 main 函数最开始）调用一次"""
        _latency_ctx.set({"metrics": {}, "starts": {}})

    @classmethod
    def start(cls, step_name: str):
        ctx = _latency_ctx.get(None)
        if ctx is not None:
            ctx["starts"][step_name] = time.perf_counter()

    @classmethod
    def stop(cls, step_name: str):
        ctx = _latency_ctx.get(None)
        if ctx is not None and step_name in ctx["starts"]:
            elapsed = (time.perf_counter() - ctx["starts"][step_name]) * 1000
            ctx["metrics"][step_name] = round(elapsed, 2)

    @classmethod
    def log_summary(cls):
        ctx = _latency_ctx.get(None)
        if not ctx:
            return
        print("\n[Latency]")
        for step in ["vector", "graph", "fusion", "llm"]:
            val = ctx["metrics"].get(step, "N/A")
            print(f"{step}: {val} ms" if val != "N/A" else f"{step}: N/A")