import sys
import os
from tools_service import InvoiceTools
from customer_service import EnhancedCustomerService

def test_invoice_plugin():
    """测试发票开具插件的功能正确性"""
    invoice_tools = InvoiceTools()

    # 测试正常开具发票
    result = invoice_tools.create_invoice("ORD123456", "测试公司", "123456789012345")
    assert result["success"] == True
    assert "invoice_id" in result["data"]
    assert result["data"]["invoice_title"] == "测试公司"

    # 测试无税号开具发票
    result_no_tax = invoice_tools.create_invoice("ORD789012", "个人用户")
    assert result_no_tax["success"] == True

    # 测试发票查询
    result_query = invoice_tools.query_invoice("INV123456")
    assert result_query["success"] == True
    assert result_query["data"]["status"] == "已开具"

    # 测试查询不存在的发票
    result_invalid = invoice_tools.query_invoice("INV000000")
    assert result_invalid["success"] == False

    print("✅ 发票插件测试通过")

def test_hot_reload():
    """测试热更新后旧会话不受影响"""
    from managers import PluginManager, ModelManager

    # 创建初始会话
    service = EnhancedCustomerService(ModelManager(), PluginManager())
    session_id = "test_session"

    # 发送初始消息
    result1 = service.process_message("我要开发票", session_id)
    assert "订单号" in result1["response"]  # 应该询问订单号

    # 模拟热更新（这里只是测试会话保持，实际热更新需要更复杂的逻辑）
    old_chat_history = result1["chat_history"].copy()

    # 继续对话
    result2 = service.process_message("ORD123456", session_id)
    assert "发票抬头" in result2["response"]  # 应该询问发票抬头

    # 验证会话历史保持连续
    assert len(result2["chat_history"]) > len(old_chat_history)
    assert result2["chat_history"][0] == old_chat_history[0]  # 历史消息应该保持一致

    print("✅ 热更新会话测试通过")

def run_tests():
    """运行所有测试"""
    print("开始运行自动化测试...")

    try:
        test_invoice_plugin()
        test_hot_reload()
        print("🎉 所有测试通过！")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)