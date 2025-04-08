"""
Celery Application Configuration
"""
import logging
import os
import warnings
from celery import Celery, Task, signals
import socket
from pathlib import Path
import sys
import time

# Ensure working directory is correct
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    'autocorrection',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['tasks.correction_tasks', 'tasks.user_tasks']
)

# Try to load configuration from environment variables first
broker_url = os.environ.get('CELERY_BROKER_URL')
result_backend = os.environ.get('CELERY_RESULT_BACKEND')

# If not configured in environment variables, use default Redis settings
if not broker_url or not result_backend:
    broker_url = 'redis://localhost:6379/0'
    result_backend = 'redis://localhost:6379/1'
    logger.info(f"Using default Redis connections: {broker_url}")

# Try to import configuration from config.celery_config
try:
    from config.celery_config import CELERY_CONFIG
    celery_app.conf.update(CELERY_CONFIG)
    logger.info("Loaded Celery standard configuration")
except ImportError as e:
    warnings.warn(f"Could not load Celery standard configuration, using built-in config: {str(e)}")
    
    # Built-in configuration - used when Redis cannot be connected
    celery_app.conf.update(
        broker_url=broker_url,
        result_backend=result_backend,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
        task_acks_late=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=500,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        task_queues={
            'default': {'exchange': 'default', 'routing_key': 'default'},
            'corrections': {'exchange': 'corrections', 'routing_key': 'correction.tasks'},
            'users': {'exchange': 'users', 'routing_key': 'user.tasks'}
        }
    )
    logger.info("Loaded Celery built-in configuration")

# Flask app context tasks
class FlaskTask(Task):
    """Task class that wraps task execution in Flask application context"""
    
    def __call__(self, *args, **kwargs):
        try:
            # 仅在需要时导入
            from app import create_app
            # 创建应用（必须在任务执行时创建）
            flask_app = create_app()
            with flask_app.app_context():
                return self.run(*args, **kwargs)
        except Exception as e:
            logger.error(f"Flask app context error: {str(e)}")
            # 如果无法创建应用上下文，仍然尝试执行任务
            return self.run(*args, **kwargs)

# Set default task type
celery_app.Task = FlaskTask

# Add retry connection logic
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Check Redis connection every minute
    sender.add_periodic_task(60.0, check_redis_connection.s(), name='check-redis-connection')

@celery_app.task
def check_redis_connection():
    """Periodically check Redis connection status and attempt to reconnect"""
    try:
        # Create Flask app to get Redis service
        from app import create_app
        flask_app = create_app()
        with flask_app.app_context():
            try:
                from app.core.services import container
                redis_service = container.get("redis_service")
                
                if redis_service and not redis_service.is_connected():
                    logger.warning("Redis connection lost, attempting to reconnect...")
                    if redis_service.reconnect():
                        logger.info("Redis reconnection successful")
                    else:
                        logger.error("Redis reconnection failed")
            except ImportError:
                logger.warning("Could not import service container, skipping Redis connection check")
    except Exception as e:
        logger.warning(f"Could not create Flask app context: {str(e)}")

# Auto-discover tasks
celery_app.autodiscover_tasks(['tasks.correction_tasks', 'tasks.user_tasks'])

# Test task
@celery_app.task(bind=True)
def debug_task(self):
    """Task for testing if Celery is working properly"""
    print(f'Request: {self.request!r}')
    return 'Celery worker is alive!'

if __name__ == '__main__':
    celery_app.start() 
