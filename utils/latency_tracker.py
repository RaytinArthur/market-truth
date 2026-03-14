import time

class LatencyTracker:
    # 核心黑科技：在类级别定义一个绝对共享的字典
    _shared_state = {
        "metrics": {},
        "_start_times": {}
    }

    def __init__(self):
        # 让所有实例的内部变量强制指向同一个字典
        self.__dict__ = self._shared_state

    def start(self, step_name: str):
        self._start_times[step_name] = time.perf_counter()

    def stop(self, step_name: str):
        if step_name in self._start_times:
            elapsed = (time.perf_counter() - self._start_times[step_name]) * 1000
            self.metrics[step_name] = round(elapsed, 2)

    def log_summary(self):
        print("\n[Latency]")
        for step in ["vector", "graph", "fusion", "llm"]:
            val = self.metrics.get(step, "N/A")
            print(f"{step}: {val} ms" if val != "N/A" else f"{step}: N/A")
            