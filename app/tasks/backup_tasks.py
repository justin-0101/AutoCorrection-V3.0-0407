#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库备份异步任务模块
处理数据库备份和恢复相关的异步任务
"""

import os
import logging
import shutil
import time
import sqlite3
import datetime
from pathlib import Path
from celery import shared_task

from app.config import config

# 获取logger
logger = logging.getLogger(__name__)

# 备份目录
BACKUP_DIR = config.BACKUP_CONFIG.get('backup_dir', 'backups')
# 保留备份的数量配置
DAILY_BACKUPS_TO_KEEP = config.BACKUP_CONFIG.get('daily_backups_to_keep', 7)
WEEKLY_BACKUPS_TO_KEEP = config.BACKUP_CONFIG.get('weekly_backups_to_keep', 4)
MONTHLY_BACKUPS_TO_KEEP = config.BACKUP_CONFIG.get('monthly_backups_to_keep', 12)
# 数据库路径
DB_PATH = config.DB_CONFIG.get('path', 'instance/essay_correction.db')


@shared_task(
    name='app.tasks.backup_tasks.backup_database',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    soft_time_limit=300,
    time_limit=360
)
def backup_database(backup_type='daily', db_path=None):
    """
    备份数据库
    
    Args:
        backup_type: 备份类型(daily/weekly/monthly)
        db_path: 数据库路径(可选)
    
    Returns:
        dict: 备份结果
    """
    start_time = time.time()
    
    try:
        logger.info(f"开始{backup_type}数据库备份")
        
        # 使用配置的数据库路径，如果没有提供
        if not db_path:
            db_path = DB_PATH
        
        # 确保备份目录存在
        backup_dir = Path(BACKUP_DIR) / backup_type
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建备份文件名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"backup_{backup_type}_{timestamp}.db"
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            logger.error(f"数据库文件不存在: {db_path}")
            return {
                "status": "error",
                "message": f"数据库文件不存在: {db_path}"
            }
        
        # 复制数据库文件
        shutil.copy2(db_path, backup_file)
        
        # 验证备份是否有效
        try:
            conn = sqlite3.connect(str(backup_file))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()[0]
            conn.close()
            
            if integrity_result != "ok":
                logger.error(f"备份文件完整性检查失败: {integrity_result}")
                return {
                    "status": "error",
                    "message": f"备份文件完整性检查失败: {integrity_result}"
                }
        except Exception as e:
            logger.error(f"备份文件验证失败: {str(e)}")
            if os.path.exists(backup_file):
                os.remove(backup_file)
            raise e
        
        # 清理旧备份
        cleanup_old_backups(backup_type)
        
        processing_time = time.time() - start_time
        logger.info(f"{backup_type}数据库备份完成，文件: {backup_file}, 耗时: {processing_time:.2f}秒")
        
        return {
            "status": "success",
            "message": f"{backup_type}数据库备份完成",
            "backup_file": str(backup_file),
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"{backup_type}数据库备份失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"{backup_type}数据库备份失败: {str(e)}"
        }


def cleanup_old_backups(backup_type):
    """
    清理旧备份文件
    
    Args:
        backup_type: 备份类型(daily/weekly/monthly)
    """
    try:
        # 获取保留的备份数量
        if backup_type == 'daily':
            backups_to_keep = DAILY_BACKUPS_TO_KEEP
        elif backup_type == 'weekly':
            backups_to_keep = WEEKLY_BACKUPS_TO_KEEP
        elif backup_type == 'monthly':
            backups_to_keep = MONTHLY_BACKUPS_TO_KEEP
        else:
            backups_to_keep = 7  # 默认值
        
        # 获取备份目录
        backup_dir = Path(BACKUP_DIR) / backup_type
        
        # 列出所有备份
        backup_files = sorted([f for f in backup_dir.glob(f"backup_{backup_type}_*.db")])
        
        # 如果备份文件数量超过限制，删除最旧的备份
        if len(backup_files) > backups_to_keep:
            for old_file in backup_files[:-backups_to_keep]:
                logger.info(f"删除旧备份文件: {old_file}")
                os.remove(old_file)
    
    except Exception as e:
        logger.error(f"清理旧备份文件失败: {str(e)}")


@shared_task(
    name='app.tasks.backup_tasks.restore_database',
    bind=True
)
def restore_database(self, backup_file, target_db_path=None):
    """
    恢复数据库备份
    
    Args:
        backup_file: 备份文件路径
        target_db_path: 目标数据库路径(可选)
    
    Returns:
        dict: 恢复结果
    """
    try:
        logger.info(f"开始恢复数据库备份，文件: {backup_file}")
        
        # 使用配置的数据库路径，如果没有提供
        if not target_db_path:
            target_db_path = DB_PATH
        
        # 检查备份文件是否存在
        if not os.path.exists(backup_file):
            logger.error(f"备份文件不存在: {backup_file}")
            return {
                "status": "error",
                "message": f"备份文件不存在: {backup_file}"
            }
        
        # 验证备份文件完整性
        try:
            conn = sqlite3.connect(backup_file)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()[0]
            conn.close()
            
            if integrity_result != "ok":
                logger.error(f"备份文件完整性检查失败: {integrity_result}")
                return {
                    "status": "error",
                    "message": f"备份文件完整性检查失败: {integrity_result}"
                }
        except Exception as e:
            logger.error(f"备份文件验证失败: {str(e)}")
            return {
                "status": "error",
                "message": f"备份文件验证失败: {str(e)}"
            }
        
        # 创建临时备份
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_backup = f"{target_db_path}.{timestamp}.bak"
        if os.path.exists(target_db_path):
            shutil.copy2(target_db_path, temp_backup)
            logger.info(f"已创建临时备份: {temp_backup}")
        
        # 恢复数据库
        try:
            shutil.copy2(backup_file, target_db_path)
            logger.info(f"数据库恢复完成，目标文件: {target_db_path}")
            
            # 删除临时备份
            if os.path.exists(temp_backup):
                os.remove(temp_backup)
                logger.info(f"已删除临时备份: {temp_backup}")
            
            return {
                "status": "success",
                "message": "数据库恢复完成",
                "restored_to": target_db_path
            }
        
        except Exception as e:
            # 如果恢复失败，尝试还原临时备份
            logger.error(f"数据库恢复失败: {str(e)}")
            if os.path.exists(temp_backup):
                shutil.copy2(temp_backup, target_db_path)
                logger.info(f"已还原临时备份: {temp_backup}")
            
            return {
                "status": "error",
                "message": f"数据库恢复失败: {str(e)}"
            }
    
    except Exception as e:
        logger.error(f"数据库恢复任务异常: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"数据库恢复任务异常: {str(e)}"
        }


@shared_task(name='app.tasks.backup_tasks.list_backups')
def list_backups(backup_type=None):
    """
    列出可用的备份
    
    Args:
        backup_type: 备份类型(daily/weekly/monthly)，如果为None则列出所有类型
    
    Returns:
        dict: 备份列表结果
    """
    try:
        # 所有可能的备份类型
        backup_types = ['daily', 'weekly', 'monthly']
        
        # 如果指定了备份类型，则只列出该类型的备份
        if backup_type:
            if backup_type not in backup_types:
                return {
                    "status": "error",
                    "message": f"无效的备份类型: {backup_type}"
                }
            backup_types = [backup_type]
        
        result = {}
        
        for btype in backup_types:
            backup_dir = Path(BACKUP_DIR) / btype
            
            # 如果目录不存在，创建一个空列表
            if not backup_dir.exists():
                result[btype] = []
                continue
            
            # 列出该类型的所有备份
            backups = []
            for backup_file in sorted(backup_dir.glob(f"backup_{btype}_*.db")):
                # 获取文件信息
                file_stats = backup_file.stat()
                # 提取时间戳
                timestamp_str = backup_file.name.replace(f"backup_{btype}_", "").replace(".db", "")
                try:
                    timestamp = datetime.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                except ValueError:
                    timestamp = None
                
                backups.append({
                    "file": str(backup_file),
                    "size": file_stats.st_size,
                    "created_at": datetime.datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "timestamp": timestamp.isoformat() if timestamp else None
                })
            
            result[btype] = backups
        
        return {
            "status": "success",
            "backups": result
        }
    
    except Exception as e:
        logger.error(f"列出备份失败: {str(e)}")
        return {
            "status": "error",
            "message": f"列出备份失败: {str(e)}"
        } 