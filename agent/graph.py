from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage

from agent.state import AgentState
from agent.tools import tools
from agent.nodes import planner_node, safety_node, reporter_node

def should_continue(state: AgentState):
    """
    核心路由大脑：流转控制器
    """
    messages = state.get("messages", [])
    step_count = state.get("step_count", 0)
    evidence_pool = state.get("evidence_pool", [])

    last_msg = messages[-1] if messages else None
    if last_msg is None:
        return "reporter"
    
    # 只要不是 AIMessage，或者 AIMessage 里没有工具调用要求，说明大模型想交卷了
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return "reporter"
    
    if step_count >= 5:
        print(f"\n[Router 拦截]触发物理硬刹车(step_count={step_count}),强制输出结论")
        return "reporter"
    

    # 严苛逻辑早停 Early Stop
    has_fact = any(e.type == "fact" for e in evidence_pool)
    has_explanation = any(e.type=="explanation" for e in evidence_pool)
    
    # 必须集齐双要素，且池子里实打实至少有2条独立证据
    if has_fact and has_explanation and len(evidence_pool) >= 2:
        print("\n[Router 拦截] 触发逻辑早停： 已集齐Fact + Explanation 且证据 >=2条， 提前交卷。")
        return "reporter"
    
    return "action"

# =================================
# 编排有向无环图 (Graph Compilation)
# =================================
workflow = StateGraph(AgentState)

# 注册节点
workflow.add_node("planner", planner_node)
workflow.add_node("action", ToolNode(tools))
workflow.add_node("safety", safety_node)
workflow.add_node("reporter", reporter_node)

# 定义起点
workflow.set_entry_point("planner")

# 核心条件分发
workflow.add_conditional_edges(
    "planner",
    should_continue,
    {
        "action": "action",
        "reporter": "reporter"
    }
)

# 勾勒固定流水线
workflow.add_edge("action", "safety")
workflow.add_edge("safety", "planner")
workflow.add_edge("reporter", END)

app = workflow.compile()