from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from config import logger, API_CONFIG
from customer_service import AppState
from models import HealthStatus

# 创建全局应用状态
app_state = AppState()

# 创建FastAPI应用
app = FastAPI(
    title="智能客服系统",
    description="支持多轮对话和工具调用的智能客服系统",
    version="1.0.0"
)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查接口"""
    current_time = datetime.now()
    uptime = current_time - datetime.fromtimestamp(app_state.start_time)

    # 检查关键组件状态
    components_healthy = True
    try:
        # 测试模型连接
        test_model = app_state.model_manager.get_model()
        test_response = test_model.invoke("测试")
        model_healthy = True
    except Exception as e:
        model_healthy = False
        components_healthy = False
        logger.error(f"模型健康检查失败: {str(e)}")

    health_status = HealthStatus(
        status="healthy" if components_healthy else "unhealthy",
        components={
            "model": "healthy" if model_healthy else "unhealthy",
            "plugins": "healthy",
            "graph": "healthy"
        },
        metrics={
            "total_requests": app_state.request_count,
            "active_sessions": len(app_state.customer_service.conversation_sessions),
            "uptime_seconds": uptime.total_seconds()
        }
    )

    status_code = 200 if components_healthy else 503
    return JSONResponse(content=health_status.__dict__, status_code=status_code)

# 对话端点
@app.post("/chat")
async def chat_endpoint(request: dict):
    """处理用户对话"""
    app_state.request_count += 1

    user_input = request.get("message", "")
    session_id = request.get("session_id")

    if not user_input:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    try:
        result = app_state.customer_service.process_message(user_input, session_id)
        return {
            "success": True,
            "response": result["response"],
            "session_id": result["session_id"],
            "current_intent": result["current_intent"],
            "tool_used": result["tool_used"]
        }
    except Exception as e:
        logger.error(f"对话处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

# 模型管理端点
@app.post("/model/update")
async def update_model(request: dict):
    """更新模型配置"""
    new_model = request.get("model_name")
    config = request.get("config")

    if not new_model:
        raise HTTPException(status_code=400, detail="模型名称不能为空")

    success = app_state.model_manager.update_model(new_model, config)

    if success:
        return {
            "success": True,
            "message": f"模型已更新为 {new_model}",
            "current_model": app_state.model_manager.current_model
        }
    else:
        raise HTTPException(status_code=500, detail="模型更新失败")

@app.get("/model/info")
async def get_model_info():
    """获取模型信息"""
    return app_state.model_manager.get_model_info()

# 插件管理端点
@app.post("/plugin/reload")
async def reload_plugin(request: dict):
    """重新加载插件"""
    plugin_name = request.get("plugin_name")

    if not plugin_name:
        raise HTTPException(status_code=400, detail="插件名称不能为空")

    success = app_state.plugin_manager.reload_plugin(plugin_name)

    if success:
        return {
            "success": True,
            "message": f"插件 {plugin_name} 重新加载成功",
            "new_version": app_state.plugin_manager.plugin_versions[plugin_name]
        }
    else:
        raise HTTPException(status_code=500, detail="插件重新加载失败")

@app.get("/plugin/info")
async def get_plugin_info():
    """获取插件信息"""
    return app_state.plugin_manager.get_plugin_info()

# 会话管理端点
@app.get("/sessions")
async def get_sessions():
    """获取活跃会话列表"""
    sessions = {}
    for session_id, session_data in app_state.customer_service.conversation_sessions.items():
        sessions[session_id] = {
            "last_activity": session_data["last_activity"],
            "message_count": len(session_data["chat_history"]) // 2
        }

    return {
        "active_sessions": len(sessions),
        "sessions": sessions
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    if session_id in app_state.customer_service.conversation_sessions:
        del app_state.customer_service.conversation_sessions[session_id]
        return {"success": True, "message": f"会话 {session_id} 已删除"}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")