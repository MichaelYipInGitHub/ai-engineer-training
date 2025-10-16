import uvicorn
from config import logger, API_CONFIG
from api import app
from test_service import run_tests

def start_server():
    """启动FastAPI服务器"""
    host = API_CONFIG["host"]
    port = API_CONFIG["port"]

    logger.info(f"启动智能客服系统服务器: http://{host}:{port}")

    # 运行自动化测试
    if run_tests():
        logger.info("自动化测试通过，启动服务器")
    else:
        logger.warning("自动化测试失败，但继续启动服务器")

    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    start_server()