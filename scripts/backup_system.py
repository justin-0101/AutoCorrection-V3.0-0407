#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统备份脚本
用于自动备份数据库和系统关键配置文件
"""

import os
import sys
import shutil
import gzip
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import json
import time
from app.core.services.file_service import FileService

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = ROOT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, 'logs', 'backup.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('backup_system')

# 备份配置
DEFAULT_BACKUP_DIR = os.environ.get('BACKUP_DIR', os.path.join(PARENT_DIR, 'AutoCorrection_Backups'))
DEFAULT_KEEP_DAYS = 30  # 默认保留30天的备份
REMOTE_BACKUP = os.environ.get('REMOTE_BACKUP_ENABLED', 'False').lower() == 'true'
REMOTE_BACKUP_PATH = os.environ.get('REMOTE_BACKUP_PATH', '')

file_service = FileService()


def ensure_backup_dir(backup_dir):
    """确保备份目录存在"""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        # 测试目录写入权限
        test_file_path = os.path.join(backup_dir, '.test_write_permission')
        with open(test_file_path, 'w') as f:
            f.write('test')
        os.remove(test_file_path)
        logger.info(f"备份目录已准备就绪: {backup_dir}")
        return True
    except PermissionError:
        logger.error(f"无法创建或写入备份目录: {backup_dir}，权限不足")
        return False
    except Exception as e:
        logger.error(f"创建备份目录失败: {backup_dir}, 错误: {str(e)}")
        return False


def backup_database(backup_dir, db_path=None):
    """
    备份数据库
    
    Args:
        backup_dir: 备份目录
        db_path: 数据库路径，如果未指定则从环境变量获取
    
    Returns:
        str: 备份文件路径
    """
    # 获取数据库路径
    if not db_path:
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            db_path = os.path.join(ROOT_DIR, db_path)
        else:
            # 对于MySQL等其他数据库，使用mysqldump等工具
            return backup_mysql_database(backup_dir)
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return None
    
    # 创建备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"db_backup_{timestamp}.sqlite"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # 对于SQLite，直接复制文件
        logger.info(f"正在备份SQLite数据库: {db_path} -> {backup_path}")
        shutil.copy2(db_path, backup_path)
        
        # 压缩备份文件
        with open(backup_path, 'rb') as f_in:
            with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 删除未压缩的文件
        os.remove(backup_path)
        compressed_path = f"{backup_path}.gz"
        
        logger.info(f"数据库备份完成: {compressed_path}")
        return compressed_path
    
    except Exception as e:
        logger.error(f"数据库备份失败: {str(e)}")
        return None


def backup_mysql_database(backup_dir):
    """
    备份MySQL数据库
    
    Args:
        backup_dir: 备份目录
    
    Returns:
        str: 备份文件路径
    """
    # 从环境变量获取数据库连接信息
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url or 'mysql' not in db_url:
        logger.error("未找到有效的MySQL数据库连接信息")
        return None
    
    # 解析数据库连接信息
    # 格式: mysql+pymysql://username:password@localhost/dbname
    try:
        db_info = db_url.split('://', 1)[1]
        auth, host_db = db_info.split('@', 1)
        username, password = auth.split(':', 1)
        host, dbname = host_db.split('/', 1)
        
        # 处理可能的查询参数
        if '?' in dbname:
            dbname = dbname.split('?', 1)[0]
    except Exception as e:
        logger.error(f"解析数据库连接信息失败: {str(e)}")
        return None
    
    # 创建备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"mysql_backup_{timestamp}.sql"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # 使用mysqldump备份
        cmd = [
            'mysqldump',
            f'--user={username}',
            f'--password={password}',
            f'--host={host}',
            '--single-transaction',
            '--quick',
            '--lock-tables=false',
            dbname
        ]
        
        logger.info(f"正在备份MySQL数据库: {dbname}")
        
        with open(backup_path, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        # 压缩备份文件
        with open(backup_path, 'rb') as f_in:
            with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 删除未压缩的文件
        os.remove(backup_path)
        compressed_path = f"{backup_path}.gz"
        
        logger.info(f"MySQL数据库备份完成: {compressed_path}")
        return compressed_path
    
    except Exception as e:
        logger.error(f"MySQL数据库备份失败: {str(e)}")
        return None


def backup_config_files(backup_dir):
    """
    备份配置文件
    
    Args:
        backup_dir: 备份目录
    
    Returns:
        str: 备份文件路径
    """
    # 要备份的配置文件列表
    config_files = [
        os.path.join(ROOT_DIR, '.env'),
        os.path.join(ROOT_DIR, '.env.example'),
        os.path.join(ROOT_DIR, 'config', 'app_config.py'),
        os.path.join(ROOT_DIR, 'config', 'celery_config.py'),
        os.path.join(ROOT_DIR, 'config', 'logging_config.py'),
    ]
    
    # 创建备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dirname = f"config_backup_{timestamp}"
    backup_dir_path = os.path.join(backup_dir, backup_dirname)
    os.makedirs(backup_dir_path, exist_ok=True)
    
    try:
        # 复制配置文件
        for config_file in config_files:
            if os.path.exists(config_file):
                dest_file = os.path.join(backup_dir_path, os.path.basename(config_file))
                shutil.copy2(config_file, dest_file)
                logger.info(f"配置文件已备份: {config_file} -> {dest_file}")
        
        # 压缩备份目录
        archive_path = f"{backup_dir_path}.tar.gz"
        shutil.make_archive(backup_dir_path, 'gztar', backup_dir_path)
        
        # 删除未压缩的目录
        shutil.rmtree(backup_dir_path)
        
        logger.info(f"配置文件备份完成: {archive_path}")
        return archive_path
    
    except Exception as e:
        logger.error(f"配置文件备份失败: {str(e)}")
        return None


def backup_uploads(backup_dir):
    """
    备份上传文件
    
    Args:
        backup_dir: 备份目录
    
    Returns:
        str: 备份文件路径
    """
    uploads_dir = os.path.join(ROOT_DIR, 'uploads')
    if not os.path.exists(uploads_dir) or not os.path.isdir(uploads_dir):
        logger.warning(f"上传目录不存在: {uploads_dir}")
        return None
    
    # 创建备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"uploads_backup_{timestamp}.tar.gz"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # 压缩上传目录
        logger.info(f"正在备份上传文件: {uploads_dir}")
        shutil.make_archive(backup_path[:-7], 'gztar', uploads_dir)
        
        logger.info(f"上传文件备份完成: {backup_path}")
        return backup_path
    
    except Exception as e:
        logger.error(f"上传文件备份失败: {str(e)}")
        return None


def sync_to_remote(backup_files):
    """
    同步备份文件到远程存储
    
    Args:
        backup_files: 备份文件列表
    
    Returns:
        bool: 是否成功
    """
    if not REMOTE_BACKUP or not REMOTE_BACKUP_PATH:
        logger.info("远程备份未启用或未配置")
        return False
    
    if not backup_files:
        logger.warning("没有备份文件需要同步")
        return False
    
    try:
        for backup_file in backup_files:
            if not backup_file or not os.path.exists(backup_file):
                continue
            
            # 根据远程路径类型选择同步方法
            if REMOTE_BACKUP_PATH.startswith('s3://'):
                # AWS S3
                cmd = ['aws', 's3', 'cp', backup_file, REMOTE_BACKUP_PATH]
            elif ':' in REMOTE_BACKUP_PATH:
                # rsync over SSH
                cmd = ['rsync', '-avz', backup_file, REMOTE_BACKUP_PATH]
            else:
                # 本地目录
                remote_dir = os.path.expanduser(REMOTE_BACKUP_PATH)
                os.makedirs(remote_dir, exist_ok=True)
                dest_path = os.path.join(remote_dir, os.path.basename(backup_file))
                shutil.copy2(backup_file, dest_path)
                logger.info(f"已复制备份文件到远程存储: {dest_path}")
                continue
            
            # 执行命令
            logger.info(f"正在同步备份文件到远程存储: {backup_file}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"备份文件已同步到远程存储: {backup_file}")
            else:
                logger.error(f"同步备份文件失败: {result.stderr}")
        
        return True
    
    except Exception as e:
        logger.error(f"同步备份文件到远程存储失败: {str(e)}")
        return False


def cleanup_old_backups(backup_dir, keep_days):
    """
    清理过期备份文件
    
    Args:
        backup_dir: 备份目录
        keep_days: 保留天数
    """
    if not os.path.exists(backup_dir):
        return
    
    try:
        current_time = time.time()
        cutoff_time = current_time - (keep_days * 24 * 60 * 60)
        
        logger.info(f"正在清理{keep_days}天前的备份文件")
        
        for filename in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, filename)
            
            # 跳过目录
            if file_service.is_directory(file_path):
                continue
            
            # 检查文件修改时间
            if file_service.get_modification_time(file_path) < cutoff_time:
                file_service.remove(file_path)
                logger.info(f"已删除过期备份文件: {file_path}")
        
        logger.info("清理过期备份文件完成")
    
    except Exception as e:
        logger.error(f"清理过期备份文件失败: {str(e)}")


def record_backup_history(backup_dir, backup_files):
    """
    记录备份历史
    
    Args:
        backup_dir: 备份目录
        backup_files: 备份文件列表
    """
    history_file = os.path.join(backup_dir, 'backup_history.json')
    
    try:
        # 加载现有历史记录
        if file_service.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        # 添加新记录
        record = {
            'timestamp': datetime.now().isoformat(),
            'files': [os.path.basename(f) for f in backup_files if f],
            'success': True
        }
        
        history.append(record)
        
        # 保存历史记录
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"备份历史已记录: {history_file}")
    
    except Exception as e:
        logger.error(f"记录备份历史失败: {str(e)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='作文批改系统备份工具')
    parser.add_argument('--backup-dir', type=str, default=DEFAULT_BACKUP_DIR,
                        help=f'备份目录，默认为{DEFAULT_BACKUP_DIR}')
    parser.add_argument('--keep-days', type=int, default=DEFAULT_KEEP_DAYS,
                        help=f'保留备份天数，默认为{DEFAULT_KEEP_DAYS}天')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='不清理过期备份文件')
    parser.add_argument('--db-only', action='store_true',
                        help='仅备份数据库')
    parser.add_argument('--config-only', action='store_true',
                        help='仅备份配置文件')
    parser.add_argument('--uploads-only', action='store_true',
                        help='仅备份上传文件')
    parser.add_argument('--no-remote', action='store_true',
                        help='不同步到远程存储')
    
    args = parser.parse_args()
    
    logger.info(f"开始系统备份，备份目录: {args.backup_dir}")
    
    # 确保备份目录存在并可写
    if not ensure_backup_dir(args.backup_dir):
        logger.error("备份目录创建或权限检查失败，无法继续备份")
        return 1
    
    backup_files = []
    
    # 备份数据库
    if not args.config_only and not args.uploads_only:
        db_backup = backup_database(args.backup_dir)
        if db_backup:
            backup_files.append(db_backup)
    
    # 备份配置文件
    if not args.db_only and not args.uploads_only:
        config_backup = backup_config_files(args.backup_dir)
        if config_backup:
            backup_files.append(config_backup)
    
    # 备份上传文件
    if not args.db_only and not args.config_only:
        uploads_backup = backup_uploads(args.backup_dir)
        if uploads_backup:
            backup_files.append(uploads_backup)
    
    if not backup_files:
        logger.warning("没有成功创建任何备份文件")
        return 1
    
    # 记录备份历史
    record_backup_history(args.backup_dir, backup_files)
    
    # 同步到远程存储
    if REMOTE_BACKUP and not args.no_remote:
        sync_to_remote(backup_files)
    
    # 清理过期备份文件
    if not args.no_cleanup:
        cleanup_old_backups(args.backup_dir, args.keep_days)
    
    logger.info("系统备份完成")
    return 0


if __name__ == '__main__':
    sys.exit(main()) 