from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class BackendConfig(AppConfig):
    name = 'backend'

    def ready(self):
        # 初始化缓存
        from backend.setup_env import client_setup
        try:
            client_setup()
        except Exception as e:
            logger.error(f"Setup environment failed: {e}")

