#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testing task logging and configuration
"""

import unittest
import os
import tempfile
import logging
import shutil
from unittest.mock import patch, MagicMock
import json
import time

from app import create_app
from app.tasks.logging_config import setup_task_logging


class TestTaskLogging(unittest.TestCase):
    """Test task logging and configuration"""
    
    def setUp(self):
        """Test setup"""
        # Create temporary log directory
        self.log_dir = tempfile.mkdtemp()
        self.old_log_dir = os.environ.get('LOG_DIR')
        os.environ['LOG_DIR'] = self.log_dir
        
        # 确保日志目录和子目录存在
        os.makedirs(os.path.join(self.log_dir, 'tasks'), exist_ok=True)
        
        # 创建应用程序实例
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Test cleanup"""
        # 关闭所有日志处理器
        loggers = [logging.getLogger('app'), 
                 logging.getLogger('app.tasks.test_task'), 
                 logging.getLogger('app.tasks.format_test'),
                 logging.getLogger('app.tasks.test_separation'),
                 logging.getLogger('json_test')]
                 
        for logger in loggers:
            for handler in list(logger.handlers):
                # 确保处理器已刷新和关闭
                if hasattr(handler, 'flush'):
                    handler.flush()
                if hasattr(handler, 'close'):
                    try:
                        handler.close()
                    except Exception:
                        pass
                # 从日志记录器中移除处理器
                logger.removeHandler(handler)
        
        # 也要关闭根日志记录器的处理器
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            try:
                handler.close()
            except Exception:
                pass
            root_logger.removeHandler(handler)
        
        # 移除应用上下文
        self.app_context.pop()
        
        # 恢复环境变量
        if self.old_log_dir:
            os.environ['LOG_DIR'] = self.old_log_dir
        else:
            del os.environ['LOG_DIR']
        
        # 在Windows上，我们需要更耐心地删除临时目录
        # 这里使用一个简单的重试机制
        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                # 逐个删除文件，而不是整个目录树
                for root, dirs, files in os.walk(self.log_dir, topdown=False):
                    for name in files:
                        file_path = os.path.join(root, name)
                        try:
                            os.remove(file_path)
                        except OSError:
                            # 如果不能删除文件，跳过它
                            pass
                    for name in dirs:
                        dir_path = os.path.join(root, name)
                        try:
                            os.rmdir(dir_path)
                        except OSError:
                            # 如果不能删除目录，跳过它
                            pass
                # 最后尝试删除根目录
                try:
                    os.rmdir(self.log_dir)
                except OSError:
                    pass
                # 如果成功到这里，跳出循环
                break
            except Exception:
                retries += 1
                # 短暂暂停后重试
                time.sleep(0.5)
    
    def test_task_logging_setup(self):
        """Test task logging setup"""
        # Call the logging setup function
        task_logger = setup_task_logging('test_task')
        
        # Verify logger level
        self.assertEqual(task_logger.level, logging.INFO)
        
        # Verify number of handlers
        self.assertGreaterEqual(len(task_logger.handlers), 1)
        
        # Verify log file exists
        log_file = os.path.join(self.log_dir, 'tasks', 'test_task.log')
        self.assertTrue(os.path.exists(os.path.dirname(log_file)))
    
    def test_task_log_format(self):
        """Test task log format"""
        # Create logger
        task_logger = setup_task_logging('format_test')
        
        # Get file handler
        file_handler = None
        for handler in task_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
                break
        
        self.assertIsNotNone(file_handler, "File handler not found")
        
        # Verify formatter
        formatter = file_handler.formatter
        self.assertIsNotNone(formatter)
        
        # Verify format string contains necessary fields
        format_str = formatter._fmt
        self.assertIn('%(asctime)s', format_str)
        self.assertIn('%(levelname)s', format_str)
        self.assertIn('%(name)s', format_str)
        self.assertIn('%(message)s', format_str)
    
    def test_log_separation(self):
        """Test application and task log separation"""
        # Setup log directory structure
        tasks_log_dir = os.path.join(self.log_dir, 'tasks')
        if not os.path.exists(tasks_log_dir):
            os.makedirs(tasks_log_dir)
        
        # Create application logger and ensure it's clean
        app_logger = logging.getLogger('app')
        # 清除现有的处理器，确保日志完全分离
        for handler in app_logger.handlers[:]:
            app_logger.removeHandler(handler)
            
        app_handler = logging.FileHandler(os.path.join(self.log_dir, 'app.log'))
        app_logger.addHandler(app_handler)
        app_logger.setLevel(logging.INFO)
        app_logger.propagate = False  # 防止日志传播到根日志记录器
        
        # Create task logger
        task_logger = setup_task_logging('test_separation')
        # 设置不传播，确保日志不会传到应用日志
        task_logger.propagate = False
        
        # Write different log messages
        app_logger.info('This is an application log message')
        task_logger.info('This is a task log message')
        
        # Flush and close handlers
        app_handler.flush()
        app_handler.close()
        for handler in task_logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
            if hasattr(handler, 'close'):
                handler.close()
        
        # Verify log files contain different messages
        with open(os.path.join(self.log_dir, 'app.log'), 'r') as f:
            app_log_content = f.read()
        
        task_log_file = os.path.join(self.log_dir, 'tasks', 'test_separation.log')
        if os.path.exists(task_log_file):
            with open(task_log_file, 'r') as f:
                task_log_content = f.read()
        else:
            task_log_content = ""
        
        self.assertIn('This is an application log message', app_log_content)
        self.assertNotIn('This is a task log message', app_log_content)
        self.assertIn('This is a task log message', task_log_content)
        self.assertNotIn('This is an application log message', task_log_content)
    
    def test_json_log_formatting(self):
        """Test JSON format logging"""
        # Create temporary JSON log file
        json_log_file = os.path.join(self.log_dir, 'json_test.log')
        
        # Create JSON handler
        json_handler = logging.FileHandler(json_log_file)
        
        # Define JSON formatter
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'name': record.name,
                    'message': record.getMessage(),
                    'filename': record.filename,
                    'lineno': record.lineno
                }
                if hasattr(record, 'task_id'):
                    log_data['task_id'] = record.task_id
                if hasattr(record, 'task_name'):
                    log_data['task_name'] = record.task_name
                return json.dumps(log_data)
        
        # Set formatter
        json_handler.setFormatter(JsonFormatter())
        
        # Create logger
        json_logger = logging.getLogger('json_test')
        json_logger.addHandler(json_handler)
        json_logger.setLevel(logging.INFO)
        
        # Add custom fields
        extra = {'task_id': 'test-123', 'task_name': 'json_test_task'}
        adapter = logging.LoggerAdapter(json_logger, extra)
        
        # Log a message
        adapter.info('This is a JSON formatted log message')
        
        # Close handler
        json_handler.close()
        
        # Verify JSON log content
        with open(json_log_file, 'r') as f:
            log_entry = json.loads(f.read())
        
        self.assertEqual(log_entry['message'], 'This is a JSON formatted log message')
        self.assertEqual(log_entry['task_id'], 'test-123')
        self.assertEqual(log_entry['task_name'], 'json_test_task')
        self.assertEqual(log_entry['level'], 'INFO')


if __name__ == '__main__':
    unittest.main() 