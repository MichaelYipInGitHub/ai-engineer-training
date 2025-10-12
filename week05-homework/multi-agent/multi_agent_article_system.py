import os
import asyncio
from typing import Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.types import Command
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
import json
import os
os.environ["OPENAI_API_KEY"] = "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"

# ------------------- 美化输出函数 -------------------
def pretty_print_message(message, indent=False):
    """美化单条消息的打印输出"""
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return
    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)

def pretty_print_messages(update, last_message=False):
    """美化并打印整个更新流中的消息"""
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        if len(ns) == 0:
            return
        graph_id = ns[-1].split(":")[0]
        print(f"来自子图 {graph_id} 的更新:")
        print("\n")
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"来自节点 {node_name} 的更新:"
        if is_subgraph:
            update_label = "\t" + update_label
        print(update_label)
        print("\n")
        messages = node_update.get("messages", [])
        if last_message and messages:
            messages = messages[-1:]
        for m in messages:
            pretty_print_message(m, indent=is_subgraph)
        print("\n")

# ------------------- 移交工具创建 -------------------
def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """创建移交工具"""
    name = f"transfer_to_{agent_name}"
    description = description or f"转移到 {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
            state: Annotated[MessagesState, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"成功转移到 {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,
            update={"messages": state["messages"] + [tool_message]},
            graph=Command.PARENT,
        )
    return handoff_tool

# 创建各个Agent的移交工具
transfer_to_researcher = create_handoff_tool(
    agent_name="researcher_agent",
    description="将任务移交给研究Agent进行主题研究"
)

transfer_to_writer = create_handoff_tool(
    agent_name="writer_agent",
    description="将任务移交给写作Agent进行文章撰写"
)

transfer_to_reviewer = create_handoff_tool(
    agent_name="reviewer_agent",
    description="将任务移交给审核Agent进行内容审核"
)

transfer_to_polisher = create_handoff_tool(
    agent_name="polisher_agent",
    description="将任务移交给润色Agent进行文章优化"
)

# ------------------- 创建各个Agent -------------------
def create_agents(mcp_tools):
    """使用MCP工具创建各个专业Agent"""

    # 研究Agent
    researcher_agent = create_react_agent(
        model="openai:gpt-3.5-turbo",
        tools=[mcp_tools[0], transfer_to_writer],  # research_tool + 移交工具
        prompt="""你是一位专业的研究员，负责对用户指定的主题进行深入研究。
                你的任务：
                1. 使用 research_topic 工具收集主题相关信息
                2. 分析研究数据，整理关键信息
                3. 当研究完成后，使用 transfer_to_writer 工具移交给写作Agent
                
                重要：确保将 research_topic 工具返回的完整JSON数据传递给写作Agent。
                不要修改或重新格式化数据，直接传递原始JSON字符串。""",
        name="researcher_agent"
    )

    # 写作Agent
    writer_agent = create_react_agent(
        model="openai:gpt-3.5-turbo",
        tools=[mcp_tools[1], mcp_tools[2], transfer_to_reviewer],  # outline + draft工具 + 移交工具
        prompt="""你是一位专业的文章写手，负责根据研究数据撰写高质量文章。
                你的任务：
                1. 使用 write_article_outline 工具创建文章大纲
                2. 使用 draft_article_section 工具撰写各个章节内容
                3. 确保文章结构清晰、内容充实
                4. 完成初稿后，使用 transfer_to_reviewer 工具移交给审核Agent
                
                重要：调用 write_article_outline 时，research_data 参数必须是 research_topic 工具返回的完整JSON字符串。
                不要修改JSON数据的内容或格式，直接使用原始数据。""",
        name="writer_agent"

    )

    # 审核Agent
    reviewer_agent = create_react_agent(
        model="openai:gpt-3.5-turbo",
        tools=[mcp_tools[3], transfer_to_polisher, transfer_to_writer],  # review工具 + 两个移交工具
        prompt="""你是一位专业的文章审核员，负责评估文章质量并提出改进建议。
                你的任务：
                1. 使用 review_article_content 工具审核文章内容
                2. 根据审核结果决定下一步：
                   - 如果文章质量合格，使用 transfer_to_polisher 移交给润色Agent
                   - 如果文章需要重大修改，使用 transfer_to_writer 返回给写作Agent重新修改
                   
                请严格把关，确保文章质量达到出版标准。""",
        name="reviewer_agent"

    )

    # 润色Agent
    polisher_agent = create_react_agent(
        model="openai:gpt-3.5-turbo",
        tools=[mcp_tools[4], mcp_tools[5]],  # polish + assemble工具
        prompt="""你是一位专业的文字编辑，负责对文章进行最后的润色和优化。
                你的任务：
                1. 使用 polish_article_content 工具优化文章语言表达
                2. 使用 assemble_final_article 工具组装最终文章
                3. 确保文章语言优美、表达准确、格式规范
                4. 完成后直接结束流程，输出最终成果""",
        name="polisher_agent"

    )

    return researcher_agent, writer_agent, reviewer_agent, polisher_agent

# ------------------- 构建多Agent工作流图 -------------------
def build_article_workflow(agents):
    """构建文章创作工作流图"""
    researcher_agent, writer_agent, reviewer_agent, polisher_agent = agents

    # 创建状态图
    workflow = StateGraph(MessagesState)

    # 添加所有Agent节点
    workflow.add_node("researcher_agent", researcher_agent)
    workflow.add_node("writer_agent", writer_agent)
    workflow.add_node("reviewer_agent", reviewer_agent)
    workflow.add_node("polisher_agent", polisher_agent)

    # 设置初始边
    workflow.add_edge(START, "researcher_agent")

    return workflow.compile()

# ------------------- 主执行函数 -------------------
async def main():
    try:
        print("正在初始化多Agent文章创作系统...")

        # 初始化MCP客户端
        client = MultiServerMCPClient({
            "article_creator": {
                "url": "http://localhost:8000/mcp",
                "transport": "streamable_http",
            }
        })

        # 在整个工作流生命周期内保持会话开启
        async with client.session("article_creator") as session:
            tools = await load_mcp_tools(session)
            print(f"已加载 {len(tools)} 个MCP工具")

            # 创建各个Agent - 注意这里直接传递tools
            agents = create_agents(tools)
            print("已创建所有专业Agent")

            # 构建工作流
            workflow = build_article_workflow(agents)
            print("工作流构建完成，准备处理用户请求...")

            # 示例用户请求
            user_requests = [
                "帮我写一篇关于AI Agent的文章",
                "请创作一篇关于机器学习的科普文章",
                "写一篇关于人工智能未来发展的文章"
            ]

            for i, user_request in enumerate(user_requests, 1):
                print(f"\n{'='*50}")
                print(f"处理请求 {i}: {user_request}")
                print(f"{'='*50}")

                # 执行工作流
                async for chunk in workflow.astream(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": user_request
                                }
                            ]
                        },
                        subgraphs=True
                ):
                    pretty_print_messages(chunk)

                print(f"\n请求 {i} 处理完成！")

                if i < len(user_requests):
                    input("\n按Enter键继续处理下一个请求...")

    except Exception as e:
        print(f"系统运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())