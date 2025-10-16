import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('customer_service.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API配置
API_CONFIG = {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": True
}

# 会话配置
SESSION_CONFIG = {
    "timeout": 3600,  # 会话超时时间（秒）
    "max_steps": 10,   # 最大对话步数
    "recursion_limit": 50  # 图递归限制
}

# 模型配置
MODEL_CONFIG = {
    "default_model": "gpt-3.5-turbo",
    "models": {
        "gpt-3.5-turbo": {
            "temperature": 0.3,
            "max_tokens": 1000
        },
        "gpt-4": {
            "temperature": 0.3,
            "max_tokens": 1000
        }
    }
}