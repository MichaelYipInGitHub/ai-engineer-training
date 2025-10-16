from typing import Dict, Any, List, TypedDict
from enum import Enum
from datetime import datetime

# 定义意图枚举
class Intent(Enum):
    QUERY_ORDER = "query_order"
    APPLY_REFUND = "apply_refund"
    CREATE_INVOICE = "create_invoice"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"

# 定义每个意图所需的信息
REQUIRED_INFO = {
    Intent.QUERY_ORDER.value: ["order_id"],
    Intent.APPLY_REFUND.value: ["order_id", "reason"],
    Intent.CREATE_INVOICE.value: ["order_id", "invoice_title", "tax_number"]
}

# 定义状态类型
class CustomerServiceState(TypedDict):
    user_input: str
    chat_history: List[Dict[str, str]]
    current_intent: str
    missing_info: Dict[str, Any]
    tool_result: Any
    response: str
    conversation_finished: bool
    step_count: int
    max_steps: int
    information_collected: bool
    information_extracted: bool

# 健康检查响应模型
class HealthStatus:
    def __init__(self, status: str, components: Dict, metrics: Dict):
        self.status = status
        self.timestamp = datetime.now().isoformat()
        self.components = components
        self.metrics = metrics
        self.version = "1.0.0"

# API响应模型
class APIResponse:
    def __init__(self, success: bool, message: str = "", data: Any = None):
        self.success = success
        self.message = message
        self.data = data
        self.timestamp = datetime.now().isoformat()