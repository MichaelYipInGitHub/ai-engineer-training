import os
import threading
import importlib
import sys
from datetime import datetime
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from tools_service import OrderTools, InvoiceTools
from config import logger, MODEL_CONFIG

class PluginManager:
    """插件管理器，支持热重载"""

    def __init__(self):
        self.plugins = {}
        self.plugin_versions = {}
        self.load_plugins()

    def load_plugins(self):
        """加载所有插件"""
        self.plugins = {
            "order_tools": OrderTools(),
            "invoice_tools": InvoiceTools()
        }
        self.plugin_versions = {
            "order_tools": "1.0.0",
            "invoice_tools": "1.0.0"
        }
        logger.info("所有插件已加载")

    def reload_plugin(self, plugin_name: str):
        """重新加载指定插件"""
        try:
            if plugin_name == "order_tools":
                # 重新加载OrderTools类
                importlib.reload(sys.modules[__name__])
                self.plugins[plugin_name] = OrderTools()
            elif plugin_name == "invoice_tools":
                # 重新加载InvoiceTools类
                importlib.reload(sys.modules[__name__])
                self.plugins[plugin_name] = InvoiceTools()

            # 更新版本号
            current_version = self.plugin_versions[plugin_name]
            major, minor, patch = current_version.split('.')
            new_version = f"{major}.{minor}.{int(patch) + 1}"
            self.plugin_versions[plugin_name] = new_version

            logger.info(f"插件 {plugin_name} 已重新加载，版本: {new_version}")
            return True
        except Exception as e:
            logger.error(f"重新加载插件 {plugin_name} 失败: {str(e)}")
            return False

    def get_plugin(self, plugin_name: str):
        """获取插件实例"""
        return self.plugins.get(plugin_name)

    def get_plugin_info(self):
        """获取所有插件信息"""
        return {
            name: {
                "version": version,
                "status": "loaded"
            } for name, version in self.plugin_versions.items()
        }

class ModelManager:
    """模型管理器，支持热更新"""

    def __init__(self):
        self.current_model = MODEL_CONFIG["default_model"]
        self.model_config = MODEL_CONFIG["models"]
        self.model_history = []
        self.update_lock = threading.Lock()

    def get_model(self, model_name: str = None):
        """获取当前模型实例"""
        if model_name is None:
            model_name = self.current_model

        config = self.model_config.get(model_name, self.model_config[MODEL_CONFIG["default_model"]])

        return ChatOpenAI(
            model_name=model_name,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

    def update_model(self, new_model: str, config: Dict[str, Any] = None):
        """更新模型配置"""
        with self.update_lock:
            old_model = self.current_model
            self.current_model = new_model

            if config:
                self.model_config[new_model] = config

            # 记录模型更新历史
            self.model_history.append({
                "timestamp": datetime.now().isoformat(),
                "from": old_model,
                "to": new_model,
                "config": self.model_config[new_model]
            })

            logger.info(f"模型已更新: {old_model} -> {new_model}")
            return True

    def get_model_info(self):
        """获取模型信息"""
        return {
            "current_model": self.current_model,
            "config": self.model_config[self.current_model],
            "available_models": list(self.model_config.keys()),
            "update_history": self.model_history[-5:]
        }