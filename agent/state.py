# 定义 图状态机 与 证据池 数据结构

from typing import Annotated, Literal, List
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

# 1. 极其严谨的证据模型(长时记忆)
class Evidence(BaseModel):
    source : str = Field(..., description="证据来源，如特定的新闻标题或图谱节点名称")
    claim : str = Field(..., description="提取的核心内容，必须保留关键数值")
    type: Literal["fact", "explanation"] = Field(
        ...,
        description="fact: 客观事件或冰冷的数据; explanation: 市场情绪或逻辑推导"
    )
    score: float = Field(default=1.0, description="证据置信度评分")

# 2. 图状态机核心 (LangGraph的血液)
class AgentState(TypedDict):
    # 使用官方的add_messages reducer, 支持追加与后续的RemoveMessage无损裁剪
    messages: Annotated[list[AnyMessage], add_messages]

    # 游历记录, 精准拦截 Graph 查询中的同义词死循环
    visited_entities: List[str]

    # 核心资产：提纯后的证据池。 触发Early Stop的唯一凭证
    evidence_pool: List[Evidence]

    # 物理硬刹车计数器，防止把 Token 烧干
    step_count: int
