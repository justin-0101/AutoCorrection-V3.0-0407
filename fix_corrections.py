#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复批改服务数据库连接问题
这个脚本会尝试定位和修复批改服务访问corrections表时出现的问题
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime
import traceback

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('correction_fix')

# 确保工作目录正确
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

def check_db_tables():
    """检查数据库表是否存在"""
    logger.info("检查数据库表结构...")
    
    db_path = os.path.join(project_root, 'instance', 'app.db')
    logger.info(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        logger.info(f"数据库中的表: {', '.join(table_names)}")
        
        # 检查corrections表是否存在
        if 'corrections' in table_names:
            logger.info("corrections表存在，检查表结构...")
            cursor.execute("PRAGMA table_info(corrections)")
            columns = cursor.fetchall()
            logger.info(f"corrections表有 {len(columns)} 个字段")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")
        else:
            logger.error("corrections表不存在！")
            return False
        
        # 检查alembic版本
        if 'alembic_version' in table_names:
            cursor.execute("SELECT * FROM alembic_version")
            version = cursor.fetchone()
            logger.info(f"当前alembic版本: {version}")
        
        conn.close()
        return 'corrections' in table_names
    except Exception as e:
        logger.error(f"检查数据库时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def check_flask_app_db():
    """使用Flask应用环境检查数据库"""
    logger.info("使用Flask应用环境检查数据库...")
    
    try:
        # 导入Flask应用
        from app import create_app
        from app.models.db import db
        from app.models.correction import Correction
        
        app = create_app()
        
        with app.app_context():
            logger.info("Flask应用上下文已创建")
            
            # 检查数据库连接
            logger.info(f"数据库URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
            
            try:
                # 尝试执行一个简单的查询
                result = db.session.execute(db.text("SELECT 1"))
                logger.info(f"数据库连接测试: {list(result)}")
                
                # 检查corrections表
                try:
                    corrections_count = db.session.query(db.func.count(Correction.id)).scalar()
                    logger.info(f"corrections表中有 {corrections_count} 条记录")
                    
                    # 尝试读取一条记录
                    correction = Correction.query.first()
                    if correction:
                        logger.info(f"成功读取一条correction记录: ID={correction.id}")
                    else:
                        logger.info("corrections表中没有记录")
                        
                except Exception as e:
                    logger.error(f"查询corrections表时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                
                # 检查模型定义
                from sqlalchemy import inspect
                mapper = inspect(Correction)
                logger.info("Correction模型定义:")
                for column in mapper.columns:
                    logger.info(f"  - {column.name}: {column.type}")
                    
            except Exception as e:
                logger.error(f"执行数据库查询时出错: {str(e)}")
                logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"创建Flask应用时出错: {str(e)}")
        logger.error(traceback.format_exc())

def modify_app_config():
    """修改应用配置以解决问题"""
    logger.info("检查应用配置...")
    
    try:
        # 导入Flask应用
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            # 打印当前配置
            logger.info("当前应用配置:")
            for key in sorted(app.config):
                if key.startswith('SQLALCHEMY'):
                    logger.info(f"  - {key}: {app.config[key]}")
            
            # 查看使用的SQLAlchemy引擎
            from app.models.db import db
            logger.info(f"SQLAlchemy引擎: {db.engine}")
            
            # 查看连接池设置
            logger.info(f"连接池大小: {db.engine.pool.size()}")
            
    except Exception as e:
        logger.error(f"检查应用配置时出错: {str(e)}")
        logger.error(traceback.format_exc())

def fix_correction_service_imports():
    """修复批改服务模块的导入问题"""
    logger.info("修复批改服务模块的导入问题...")
    
    # 导入process_pending_corrections模块
    try:
        import scripts.utils.process_pending_corrections as ppc
        logger.info("成功导入process_pending_corrections模块")
        
        # 检查模块内的导入
        logger.info("检查模块内的导入:")
        import importlib
        for module_name in [
            'app.models.correction', 
            'app.models.essay', 
            'app.tasks.correction_tasks'
        ]:
            try:
                module = importlib.import_module(module_name)
                logger.info(f"  - 成功导入 {module_name}")
            except Exception as e:
                logger.error(f"  - 导入 {module_name} 失败: {str(e)}")
                
    except Exception as e:
        logger.error(f"导入process_pending_corrections模块时出错: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    """主函数"""
    logger.info("开始修复批改服务问题...")
    
    # 检查数据库表
    if not check_db_tables():
        logger.error("数据库表检查失败，无法继续修复")
        return
    
    # 检查Flask应用数据库
    check_flask_app_db()
    
    # 修改应用配置
    modify_app_config()
    
    # 修复批改服务导入
    fix_correction_service_imports()
    
    logger.info("修复过程完成")

if __name__ == "__main__":
    main() 