import re
from datetime import datetime, timedelta
from langchain.prompts import PromptTemplate
from models import CustomerServiceState, Intent, REQUIRED_INFO
from config import logger

class GraphNodes:
    """LangGraph节点函数集合"""

    def __init__(self, model_manager, plugin_manager):
        self.model_manager = model_manager
        self.plugin_manager = plugin_manager

    def intent_recognition_node(self, state: CustomerServiceState) -> CustomerServiceState:
        """识别用户意图"""
        state["step_count"] += 1

        # 检查步骤限制
        if state["step_count"] > state["max_steps"]:
            state["response"] = "抱歉，对话轮次过多，请重新开始咨询。"
            state["conversation_finished"] = True
            return state

        intent_prompt = PromptTemplate(
            template="""根据用户输入识别意图。可选意图：
- query_order: 用户想要查询订单状态
- apply_refund: 用户想要申请退款
- create_invoice: 用户想要开具发票
- general_query: 一般咨询问题

用户输入: {user_input}
对话历史: {chat_history}

请只返回意图名称，不要返回其他内容。""",
            input_variables=["user_input", "chat_history"]
        )

        llm = self.model_manager.get_model()

        chat_history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in state["chat_history"][-3:]
        ]) if state["chat_history"] else "无"

        try:
            intent_result = llm.invoke(intent_prompt.format(
                user_input=state["user_input"],
                chat_history=chat_history_text
            ))

            intent_str = intent_result.content.strip().lower()
            state["current_intent"] = intent_str

        except Exception:
            # 如果LLM调用失败，使用基于关键词的后备方案
            user_input_lower = state["user_input"].lower()
            if any(keyword in user_input_lower for keyword in ["查询", "订单", "查订单"]):
                state["current_intent"] = Intent.QUERY_ORDER.value
            elif any(keyword in user_input_lower for keyword in ["退款", "退货"]):
                state["current_intent"] = Intent.APPLY_REFUND.value
            elif any(keyword in user_input_lower for keyword in ["发票", "开票", "发票开具"]):
                state["current_intent"] = Intent.CREATE_INVOICE.value
            else:
                state["current_intent"] = Intent.GENERAL_QUERY.value

        return state

    def information_collection_node(self, state: CustomerServiceState) -> CustomerServiceState:
        """收集执行工具所需的信息"""
        state["step_count"] += 1

        # 确保missing_info存在
        if "missing_info" not in state:
            state["missing_info"] = {}

        # 获取当前意图所需的信息字段
        required_fields = REQUIRED_INFO.get(state["current_intent"], [])

        # 确保missing_info包含所有必需字段
        for field in required_fields:
            if field not in state["missing_info"]:
                state["missing_info"][field] = None

        # 根据意图和缺失信息生成相应的询问
        if state["current_intent"] == Intent.QUERY_ORDER.value:
            if state["missing_info"]["order_id"] is None:
                state["response"] = "请问您的订单号是多少？"
                state["information_extracted"] = False
            else:
                state["information_collected"] = True
                return state

        elif state["current_intent"] == Intent.APPLY_REFUND.value:
            if state["missing_info"]["order_id"] is None:
                state["response"] = "请问您要申请退款的订单号是多少？"
                state["information_extracted"] = False
            elif state["missing_info"]["reason"] is None:
                state["response"] = "请问您申请退款的原因是什么？"
                state["information_extracted"] = False
            else:
                state["information_collected"] = True
                return state

        elif state["current_intent"] == Intent.CREATE_INVOICE.value:
            if state["missing_info"]["order_id"] is None:
                state["response"] = "请问您要为哪个订单开具发票？请提供订单号。"
                state["information_extracted"] = False
            elif state["missing_info"]["invoice_title"] is None:
                state["response"] = "请问发票抬头是什么？"
                state["information_extracted"] = False
            elif state["missing_info"]["tax_number"] is None:
                state["response"] = "请问纳税人识别号是什么？（如不需要可回复'无'）"
                state["information_extracted"] = False
            else:
                state["information_collected"] = True
                return state

        return state

    def information_extraction_node(self, state: CustomerServiceState) -> CustomerServiceState:
        """从用户输入中提取所需信息"""
        state["step_count"] += 1

        # 确保missing_info存在
        if "missing_info" not in state:
            state["missing_info"] = {}

        if state["current_intent"] in [Intent.QUERY_ORDER.value, Intent.APPLY_REFUND.value, Intent.CREATE_INVOICE.value]:
            # 获取当前意图所需的信息字段
            required_fields = REQUIRED_INFO.get(state["current_intent"], [])

            # 确保所有必需字段都在missing_info中
            for field in required_fields:
                if field not in state["missing_info"]:
                    state["missing_info"][field] = None

            # 提取订单号
            order_match = re.search(r'[A-Za-z]{3}\d{6,}', state["user_input"])
            if order_match and state["missing_info"].get("order_id") is None:
                state["missing_info"]["order_id"] = order_match.group().upper()

            # 提取发票抬头和税号
            if state["current_intent"] == Intent.CREATE_INVOICE.value:
                # 简单的发票抬头提取（假设用户直接提供了抬头）
                if state["missing_info"].get("invoice_title") is None and len(state["user_input"]) > 2:
                    # 如果不是订单号和税号，且长度合适，认为是发票抬头
                    if not order_match and not re.search(r'\d{15,20}', state["user_input"]):
                        state["missing_info"]["invoice_title"] = state["user_input"]

                # 提取税号（15-20位数字）
                tax_match = re.search(r'\d{15,20}', state["user_input"])
                if tax_match and state["missing_info"].get("tax_number") is None:
                    state["missing_info"]["tax_number"] = tax_match.group()

                # 如果用户说"无"或"不需要"，设置税号为空
                if "无" in state["user_input"] or "不需要" in state["user_input"]:
                    state["missing_info"]["tax_number"] = ""

            # 如果是退款申请且还没有原因，尝试提取原因
            if (state["current_intent"] == Intent.APPLY_REFUND.value and
                    state["missing_info"].get("order_id") and
                    state["missing_info"].get("reason") is None):

                # 简单的关键词提取
                reason_keywords = {
                    "质量": "商品质量问题",
                    "损坏": "商品损坏",
                    "不满意": "对商品不满意",
                    "错误": "订单信息错误",
                    "不想要": "不再需要此商品",
                    "不喜欢": "对商品不喜欢"
                }

                for keyword, reason in reason_keywords.items():
                    if keyword in state["user_input"]:
                        state["missing_info"]["reason"] = reason
                        break

                if not state["missing_info"].get("reason"):
                    # 如果没有匹配到关键词，使用用户原始输入作为原因
                    state["missing_info"]["reason"] = state["user_input"]

        state["information_extracted"] = True
        return state

    def tool_call_node(self, state: CustomerServiceState) -> CustomerServiceState:
        """调用相应的工具函数"""
        state["step_count"] += 1

        # 确保missing_info存在
        if "missing_info" not in state:
            state["missing_info"] = {}

        if state["current_intent"] == Intent.QUERY_ORDER.value and state["missing_info"].get("order_id"):
            order_tools = self.plugin_manager.get_plugin("order_tools")
            result = order_tools.query_order(state["missing_info"]["order_id"])
            state["tool_result"] = result

            if result["success"]:
                order = result["data"]
                state["response"] = f"订单状态: {order['status']}\n"
                state["response"] += f"商品: {order['product']}\n"
                state["response"] += f"下单日期: {order['order_date']}\n"
                state["response"] += f"预计送达: {order['estimated_delivery']}"

                if order.get("tracking_number"):
                    state["response"] += f"\n快递公司: {order['shipping_company']}"
                    state["response"] += f"\n运单号: {order['tracking_number']}"
            else:
                state["response"] = f"抱歉，{result['error']}"

            state["conversation_finished"] = True

        elif state["current_intent"] == Intent.APPLY_REFUND.value and state["missing_info"].get("order_id") and state["missing_info"].get("reason"):
            order_tools = self.plugin_manager.get_plugin("order_tools")
            result = order_tools.apply_refund(
                state["missing_info"]["order_id"],
                state["missing_info"]["reason"]
            )
            state["tool_result"] = result
            state["response"] = result["message"]
            state["conversation_finished"] = True

        elif state["current_intent"] == Intent.CREATE_INVOICE.value and state["missing_info"].get("order_id") and state["missing_info"].get("invoice_title"):
            invoice_tools = self.plugin_manager.get_plugin("invoice_tools")
            result = invoice_tools.create_invoice(
                state["missing_info"]["order_id"],
                state["missing_info"]["invoice_title"],
                state["missing_info"].get("tax_number")
            )
            state["tool_result"] = result
            state["response"] = result["message"]
            state["conversation_finished"] = True

        return state

    def general_response_node(self, state: CustomerServiceState) -> CustomerServiceState:
        """处理一般性查询"""
        state["step_count"] += 1

        if state["current_intent"] == Intent.GENERAL_QUERY.value:
            prompt_template = PromptTemplate(
                input_variables=["time_context", "user_input", "chat_history"],
                template="""你是一个智能客服助手，需要准确理解用户的时间相关查询，并结合当前时间进行回答。

{time_context}

对话历史:
{chat_history}

用户输入: {user_input}

请提供有帮助的回复。

客服回复:"""
            )

            llm = self.model_manager.get_model()

            # 获取时间上下文
            now = datetime.now()
            current_time = now.strftime("%Y年%m月%d日 %H:%M:%S")
            yesterday = (now - timedelta(days=1)).strftime("%Y年%m月%d日")
            tomorrow = (now + timedelta(days=1)).strftime("%Y年%m月%d日")

            time_context = f"""
当前时间: {current_time}
相关日期:
- 昨天: {yesterday}
- 今天: {now.strftime('%Y年%m月%d日')}
- 明天: {tomorrow}
"""

            # 获取对话历史
            chat_history_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in state["chat_history"][-3:]
            ]) if state["chat_history"] else "无"

            try:
                result = llm.invoke(prompt_template.format(
                    time_context=time_context,
                    user_input=state["user_input"],
                    chat_history=chat_history_text
                ))

                state["response"] = result.content
            except Exception:
                state["response"] = "抱歉，我现在无法处理您的请求，请稍后再试。"

            state["conversation_finished"] = True

        return state

    def update_history_node(self, state: CustomerServiceState) -> CustomerServiceState:
        """更新对话历史"""
        # 添加用户消息到历史
        state["chat_history"].append({
            "role": "user",
            "content": state["user_input"]
        })

        # 添加AI响应到历史
        if state["response"]:
            state["chat_history"].append({
                "role": "assistant",
                "content": state["response"]
            })

        return state

    def route_conversation(self, state: CustomerServiceState) -> str:
        """决定下一步执行哪个节点"""

        # 如果已经生成响应，更新历史后结束
        if state.get("response"):
            return "update_history"

        # 如果对话已结束，更新历史后结束
        if state.get("conversation_finished", False):
            return "update_history"

        # 检查步骤限制
        if state.get("step_count", 0) > state.get("max_steps", 20):
            state["response"] = "为了更好的服务体验，本次对话将结束。如有需要请重新咨询。"
            return "update_history"

        current_intent = state.get("current_intent", Intent.UNKNOWN.value)

        # 一般查询直接回复
        if current_intent == Intent.GENERAL_QUERY.value:
            return "general_response"

        # 工具类意图的处理流程
        # 获取当前意图所需的信息字段
        required_fields = REQUIRED_INFO.get(current_intent, [])

        # 确保missing_info存在
        if "missing_info" not in state:
            state["missing_info"] = {}

        # 确保missing_info包含所有必需字段
        for field in required_fields:
            if field not in state["missing_info"]:
                state["missing_info"][field] = None

        # 检查是否所有必需信息都已收集
        all_info_collected = all(state["missing_info"].get(field) is not None for field in required_fields)

        if all_info_collected:
            return "tool_call"
        else:
            # 如果有用户输入但还没有响应，尝试提取信息
            if not state.get("information_extracted", False):
                return "information_extraction"
            elif not state.get("information_collected", False):
                return "information_collection"
            else:
                return "information_collection"