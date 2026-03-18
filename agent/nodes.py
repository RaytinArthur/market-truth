# planner_node（大脑）：只负责根据规则调工具
# safety_node（安检门与记忆刺客）: 
#   拦截工具返回的长文本，
#   把核心线索（Evidence）压入长时记忆池后，直接调用 RemoveMessage 把那长文本从上下文队列里“精准刺杀”

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, RemoveMessage, ToolMessage, AIMessage, HumanMessage
from pydantic import BaseModel, Field

from agent.state import AgentState, Evidence
from agent.tools import tools
from agent.prompts import PLANNER_PROMPT, REPORTER_PROMPT

from config import (
    MODEL_NAME, OPENAI_BASE_URL,OPENAI_API_KEY
)

# 极简提炼schema,减轻LLM结构化输出的负担
class ExtractedEvidence(BaseModel):
    claim: str = Field(..., description="Short evidence statement under 25 words")
    type: str = Field(..., description="'fact' or 'explanation'")

class ExtractedEvidences(BaseModel):
    items: list[ExtractedEvidence]

# 1. 初始化大脑 并绑定武器
llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
    temperature=0.1,
    max_tokens=800
)

planner_llm = llm.bind_tools(tools)
extractor_llm = llm.with_structured_output(ExtractedEvidences)

# 2. 决策节点（纯净大脑）
def planner_node(state: AgentState):
    """
    职责：纯推理与工具调度
    """
    messages = state.get("messages", [])
    step_count = state.get("step_count", 0)

    # 补丁1：解决System Prompt 叠加污染的问题
    # 无论图怎么循环，先把上下文中可能存在的旧 SystemMessage 剃掉
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    # 注入携带当前部署的最新System Prompt
    sys_msg = SystemMessage(content=PLANNER_PROMPT.format(step_count=step_count))
    input_messages = [sys_msg] + filtered_messages

    # 执行推理
    response = planner_llm.invoke(input_messages)

    return {"messages": [response]}

# 3. 安检与上下文裁剪节点 (Memory Assasin)
def safety_node(state: AgentState):
    """
    职责：提取精华-> 更新证据池 -> 斩杀冗长历史
    """
    messages = state.get("messages", [])
    evidence_pool = state.get("evidence_pool", [])
    visited_entities = state.get("visited_entities", [])
    step_count = state.get("step_count", 0)

    # 预先找到最近的发号施令 AIMessage (用于匹配工具参数)
    last_ai_msg = next((m for m in reversed(messages) if isinstance(m, AIMessage) and m.tool_calls), None)

    # 1. 倒序处理当前轮次的所有并发 ToolMessage
    recent_tool_messages = []
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            break
        recent_tool_messages.append(msg)
        
    for tool_msg in recent_tool_messages:
        content_str = str(tool_msg.content)
        
        # 记录游历实体 (强校验 name，并容错参数字段)
        if tool_msg.name == "graph_search" and last_ai_msg:
            for tc in last_ai_msg.tool_calls:
                if tc["id"] == tool_msg.tool_call_id and tc["name"] == "graph_search":
                    args = tc.get("args", {})
                    entity = args.get("ticker") or args.get("symbol") or args.get("entity")
                    if entity and entity not in visited_entities:
                        visited_entities.append(entity)
        
        # 阈值过滤与小模型极简提炼
        if "Error" not in content_str and len(content_str) > 800:
            prompt = f"""
            Extract up to TWO short financial evidence statements from this tool output.
            Rules:
            - Each statement < 25 words
            - Classify as 'fact' or 'explanation'
            - Do not summarize the whole article, just extract the core anomaly reason.

            Tool Output:
            {content_str}
            """
            try:
                extracted = extractor_llm.invoke(prompt)
                if extracted and extracted.items:
                    for item in extracted.items:
                        evidence_pool.append(Evidence(
                            source=tool_msg.name,
                            claim=item.claim,
                            type=item.type,
                            score=0.8  # 硬编码置信度，把非确定性剥离
                        ))
            except Exception as e:
                print(f"[Safety Node] Extraction failed: {e}")
    

    # 补丁2：精准刺杀，拒绝暴利切片
    delete_targets = []
    # 永远保留最新的一次查询结果（供下一步Planner推理或者Reporter总结使用）
    safe_tool_ids = {m.tool_call_id for m in recent_tool_messages}
    
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.tool_call_id not in safe_tool_ids:
            # 安全计算长度
            content_len = len(msg.content) if isinstance(msg.content, str) else len(str(msg.content))
            # 如果是历史残留的超大json/文本， 精准抹除
            if content_len > 500:
                delete_targets.append(RemoveMessage(id=msg.id))

    # 补丁 3：必须显式返回所有被修改的 mutable 对象，否则状态不会更新！
    return {
        "step_count": step_count + 1,       
        "messages": delete_targets,         
        "evidence_pool": evidence_pool,     
        "visited_entities": visited_entities
    }

# 4. 临终遗言节点
def reporter_node(state: AgentState):
    """
    职责：禁用工具，只读evidence_pool,写出拿份极度严谨的SSE流式报告
    """
    evidence_pool = state.get("evidence_pool", [])

    # 把 高维的Evidence对象降维成String，喂给大模型
    if evidence_pool:
        evidence_text = "\n".join([f"[{e.type.upper()}] 来源：{e.source} | 结论：{e.claim}" for e in evidence_pool])
    else:
        evidence_text = "目前没有收集到任何有效证据，请如实输出信息缺口"
    
    sys_msg = SystemMessage(content=REPORTER_PROMPT)
    user_msg = HumanMessage(content=f"请根据以下收集到的线索进行归因总结：\n {evidence_text}")

    # 2. 调用纯净的llm
    response = llm.invoke([sys_msg, user_msg])

    # 3. 覆盖messages, 确保护航最后一步输出干净的报告
    return {"messages": [response]}