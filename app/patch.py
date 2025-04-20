#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
猴子补丁应用模块
用于应用必要的猴子补丁，确保各个库能够正常协同工作
"""

# 在导入任何其他模块之前应用eventlet补丁
import os
import sys

# 标记变量，避免重复应用补丁
_EVENTLET_PATCHED = False
_SQLALCHEMY_PATCHED = False

def apply_eventlet_patch_early():
    """
    在导入任何其他模块之前应用eventlet补丁
    """
    global _EVENTLET_PATCHED
    
    # 如果已经应用了补丁，直接返回
    if _EVENTLET_PATCHED or os.environ.get('EVENTLET_PATCHED') == 'true':
        return True
    
    # 检查是否需要应用Eventlet补丁
    worker_pool = os.environ.get('CELERY_WORKER_POOL', '').lower()
    if worker_pool == 'eventlet' or 'eventlet' in sys.argv:
        try:
            import eventlet
            # 在导入其他模块前应用eventlet补丁
            eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)
            
            # 标记已应用补丁
            os.environ['EVENTLET_PATCHED'] = 'true'
            _EVENTLET_PATCHED = True
            
            # 稍后会设置日志，这里只打印到标准输出
            print("eventlet猴子补丁已成功应用")
            return True
        except ImportError:
            print("警告: 未安装eventlet，请执行 pip install eventlet")
            return False
        except Exception as e:
            print(f"应用eventlet猴子补丁时出错: {str(e)}")
            return False
    return False

# 立即应用eventlet补丁
apply_eventlet_patch_early()

# 导入其他模块
import logging
from threading import local as threading_local

# 设置基础日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_sqlalchemy_queue():
    """修复SQLAlchemy队列通知问题"""
    global _SQLALCHEMY_PATCHED
    
    if _SQLALCHEMY_PATCHED:
        return True
        
    try:
        # 方法1: 修复Queue.notify
        import queue
        # 如果Queue没有notify方法，则添加
        if not hasattr(queue.Queue, 'notify'):
            # 添加一个空的notify方法
            queue.Queue.notify = lambda self: None
            logger.info("已添加Queue.notify空方法补丁")
        
        # 方法2: 修补SQLAlchemy的互斥锁，避免循环导入
        try:
            import sqlalchemy.util.queue
            if hasattr(sqlalchemy.util.queue, 'Queue'):
                original_notify = getattr(sqlalchemy.util.queue.Queue, 'notify', None)
                
                # 如果原方法存在，定义安全的notify方法
                if original_notify:
                    def safe_notify(self):
                        if not hasattr(self, 'mutex') or not self.mutex.locked():
                            return
                        return original_notify(self)
                        
                    # 应用补丁
                    sqlalchemy.util.queue.Queue.notify = safe_notify
                    logger.info("已修补SQLAlchemy Queue.notify方法")
                else:
                    # 如果原方法不存在，添加空方法
                    sqlalchemy.util.queue.Queue.notify = lambda self: None
                    logger.info("已添加SQLAlchemy Queue.notify空方法")
        except ImportError:
            logger.debug("未找到sqlalchemy.util.queue模块，跳过修补")
        except Exception as e:
            logger.warning(f"修补SQLAlchemy.util.queue时出错: {str(e)}")
        
        _SQLALCHEMY_PATCHED = True
        return True
    except Exception as e:
        logger.error(f"修复SQLAlchemy队列通知问题失败: {e}")
        return False

# 立即应用SQLAlchemy修复
fix_sqlalchemy_queue()

def is_eventlet_patched():
    """
    检查当前环境是否已应用Eventlet补丁
    """
    if os.environ.get('EVENTLET_PATCHED') == 'true' or _EVENTLET_PATCHED:
        return True
        
    try:
        import eventlet
        return eventlet.patcher.is_monkey_patched('thread')
    except ImportError:
        return False

def apply_eventlet_patch():
    """
    应用Eventlet补丁以确保与异步IO和SQLAlchemy的兼容性
    
    此函数必须在应用启动时最早调用，以确保所有I/O操作都被正确补丁
    """
    global _EVENTLET_PATCHED
    
    # 如果已经应用了补丁，直接返回
    if is_eventlet_patched():
        logger.info("eventlet补丁已应用，跳过重复应用")
        return True
    
    logger.info("准备应用Eventlet补丁...")
    
    # 检查是否需要应用Eventlet补丁
    worker_pool = os.environ.get('CELERY_WORKER_POOL', '').lower()
    if worker_pool != 'eventlet' and 'eventlet' not in sys.argv:
        logger.info(f"当前工作池不是eventlet ({worker_pool})，跳过应用补丁")
        return False
    
    try:
        import eventlet
        
        # 应用补丁
        eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)
        
        # 标记已应用补丁
        os.environ['EVENTLET_PATCHED'] = 'true'
        _EVENTLET_PATCHED = True
        
        logger.info("Eventlet补丁已成功应用")
        return True
        
    except ImportError as e:
        logger.error(f"应用Eventlet补丁失败: {e}")
        logger.error("请确保已安装eventlet: pip install eventlet")
        return False
    except Exception as e:
        logger.error(f"应用Eventlet补丁时发生未知错误: {e}")
        return False

def apply_sqlalchemy_patch():
    """应用SQLAlchemy连接池补丁，处理与eventlet的兼容性问题"""
    try:
        # 修复Queue.notify问题
        fix_sqlalchemy_queue()
        
        # 这个函数会在app/__init__.py中被调用
        # 具体的SQLAlchemy配置修改已在app/extensions.py中完成
        logger.info("SQLAlchemy补丁已应用")
        return True
    except Exception as e:
        logger.error(f"应用SQLAlchemy补丁时出错: {str(e)}")
        return False

def apply_patches():
    """应用所有必要的猴子补丁"""
    logger.info("检查已应用的补丁状态...")
    
    # 应用eventlet补丁
    eventlet_result = apply_eventlet_patch()
    
    # 应用SQLAlchemy补丁
    sqlalchemy_result = apply_sqlalchemy_patch()
    
    # 检查补丁应用结果
    if eventlet_result and sqlalchemy_result:
        logger.info("所有补丁已成功应用")
        return True
    else:
        patches_status = []
        if not eventlet_result:
            patches_status.append("eventlet")
        if not sqlalchemy_result:
            patches_status.append("SQLAlchemy")
            
        logger.warning(f"部分补丁应用失败: {', '.join(patches_status)}")
        return False 