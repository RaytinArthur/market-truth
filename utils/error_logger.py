import json
import os
import logging
from enum import Enum
from datetime import datetime

# 1. 定义核心错误类型枚举，防止拼写手误
class ErrorType(Enum):
    ENTITY_ALIGNMENT_FAILURE = "entity_alignment_failure"       # 实体对齐失败
    GRAPH_EVIDENCE_MISSING = "graph_evidence_missing"           # 图谱证据缺失
    LLM_HALLUCINATION = "llm_hallucination"                     # 大模型幻觉
    CONFLICT_PROCESSING_ERROR = "conflict_processing_error"     # 冲突证据处理错误

# 初始化基础 logger（用于控制台提示）
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ErrorTracker")

# 设定日志统一落盘目录 (放在项目根目录的 logs 文件夹下)
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error_analysis.jsonl")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)

def log_error(
    error_type: ErrorType, 
    query: str = "", 
    context: str = "", 
    response: str = "", 
    details: dict = None
):
    """
    统一错误打点函数
    将案发现场的所有线索（Query, Context, LLM输出）打包成单行 JSON 写入日志。
    """
    if details is None:
        details = {}

    # 构造标准化的错误结构体
    error_record = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type.value,
        "query": query,
        # 记录长度以便快速筛查是不是 context 截断爆 token 了
        "context_length": len(context) if context else 0, 
        "context": context,
        "response": response,
        "details": details  # 存放各个错误特定的补充信息（比如对齐失败的实体名）
    }

    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_record, ensure_ascii=False) + "\n")
        logger.warning(f"🚨 捕获并记录异常: [{error_type.value}] | Query: {query[:20]}...")
    except Exception as e:
        logger.error(f"写入 JSONL 错误日志失败: {e}")

# 测试运行
if __name__ == "__main__":
    log_error(
        ErrorType.LLM_HALLUCINATION,
        query="CRNX为什么大跌？",
        context="无相关信息",
        response="因为财报不及预期...",
        details={"suspected_hallucination": "财报不及预期"}
    )