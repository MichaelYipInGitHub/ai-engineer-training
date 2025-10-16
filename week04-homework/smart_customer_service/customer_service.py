import time
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from models import CustomerServiceState, Intent
from config import logger, SESSION_CONFIG
from graph_nodes import GraphNodes

class EnhancedCustomerService:
    """支持多轮对话和工具调用的客服系统"""

    def __init__(self, model_manager, plugin_manager, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.model_manager = model_manager
        self.plugin_manager = plugin_manager
        self.graph_nodes = GraphNodes(model_manager, plugin_manager)
        self.graph = self._create_customer_service_graph()
        self.conversation_sessions = {}  # 存储会话状态
        self.session_timeout = SESSION_CONFIG["timeout"]

    def _create_customer_service_graph(self):
        """创建客服对话图"""
        workflow = StateGraph(CustomerServiceState)

        # 添加节点
        workflow.add_node("intent_recognition", self.graph_nodes.intent_recognition_node)
        workflow.add_node("information_collection", self.graph_nodes.information_collection_node)
        workflow.add_node("information_extraction", self.graph_nodes.information_extraction_node)
        workflow.add_node("tool_call", self.graph_nodes.tool_call_node)
        workflow.add_node("general_response", self.graph_nodes.general_response_node)
        workflow.add_node("update_history", self.graph_nodes.update_history_node)

        # 设置入口点
        workflow.set_entry_point("intent_recognition")

        # 条件边
        workflow.add_conditional_edges(
            "intent_recognition",
            self.graph_nodes.route_conversation,
            {
                "information_collection": "information_collection",
                "information_extraction": "information_extraction",
                "tool_call": "tool_call",
                "general_response": "general_response",
                "update_history": "update_history"
            }
        )

        workflow.add_conditional_edges(
            "information_collection",
            self.graph_nodes.route_conversation,
            {
                "information_collection": "information_collection",
                "information_extraction": "information_extraction",
                "tool_call": "tool_call",
                "general_response": "general_response",
                "update_history": "update_history"
            }
        )

        workflow.add_conditional_edges(
            "information_extraction",
            self.graph_nodes.route_conversation,
            {
                "information_collection": "information_collection",
                "tool_call": "tool_call",
                "general_response": "general_response",
                "update_history": "update_history"
            }
        )

        workflow.add_conditional_edges(
            "tool_call",
            self.graph_nodes.route_conversation,
            {
                "update_history": "update_history"
            }
        )

        workflow.add_conditional_edges(
            "general_response",
            self.graph_nodes.route_conversation,
            {
                "update_history": "update_history"
            }
        )

        # 添加最终边
        workflow.add_edge("update_history", END)

        return workflow.compile()

    def _cleanup_sessions(self):
        """清理过期的会话"""
        current_time = time.time()
        expired_sessions = []

        for session_id, session_data in self.conversation_sessions.items():
            if current_time - session_data.get("last_activity", 0) > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.conversation_sessions[session_id]
            logger.info(f"清理过期会话: {session_id}")

    def process_message(self, user_input: str, session_id: str = None, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """处理用户消息"""

        # 清理过期会话
        self._cleanup_sessions()

        if session_id is None:
            session_id = f"session_{int(time.time())}_{id(self)}"

        if chat_history is None:
            if session_id in self.conversation_sessions:
                chat_history = self.conversation_sessions[session_id]["chat_history"]
            else:
                chat_history = []

        # 准备初始状态
        initial_state = {
            "user_input": user_input,
            "chat_history": chat_history,
            "current_intent": Intent.UNKNOWN.value,
            "missing_info": {},
            "tool_result": None,
            "response": "",
            "conversation_finished": False,
            "step_count": 0,
            "max_steps": SESSION_CONFIG["max_steps"],
            "information_collected": False,
            "information_extracted": False
        }

        try:
            # 执行图，显式设置递归限制
            config = {"recursion_limit": SESSION_CONFIG["recursion_limit"]}
            final_state = self.graph.invoke(initial_state, config=config)

            # 更新会话状态
            self.conversation_sessions[session_id] = {
                "chat_history": final_state["chat_history"],
                "last_activity": time.time()
            }

            return {
                "response": final_state["response"],
                "chat_history": final_state["chat_history"],
                "current_intent": final_state["current_intent"],
                "tool_used": final_state.get("tool_result") is not None,
                "session_id": session_id
            }
        except Exception as e:
            # 错误处理
            logger.error(f"处理消息时出错: {str(e)}")
            error_response = "抱歉，系统暂时无法处理您的请求，请稍后再试。"
            chat_history.extend([
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": error_response}
            ])

            # 更新会话状态
            self.conversation_sessions[session_id] = {
                "chat_history": chat_history,
                "last_activity": time.time()
            }

            return {
                "response": error_response,
                "chat_history": chat_history,
                "current_intent": Intent.UNKNOWN.value,
                "tool_used": False,
                "session_id": session_id
            }

# 全局应用状态
class AppState:
    def __init__(self):
        from managers import PluginManager, ModelManager
        self.plugin_manager = PluginManager()
        self.model_manager = ModelManager()
        self.customer_service = EnhancedCustomerService(self.model_manager, self.plugin_manager)
        self.start_time = time.time()
        self.request_count = 0