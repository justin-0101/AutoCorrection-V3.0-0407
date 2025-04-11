#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
更新数据库约束脚本
为essays和corrections表添加processing状态的支持
"""

import sys
import os
from pathlib import Path
import logging
from sqlalchemy import text

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_constraints():
    """更新数据库约束以支持processing状态"""
    try:
        from alembic import op
        import sqlalchemy as sa
        
        logger.info("开始更新数据库约束...")
        
        # 更新essays表的约束
        logger.info("更新essays表的约束...")
        # 先删除旧的约束
        with op.batch_alter_table('essays', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('valid_status', type_='check')
            except Exception as e:
                logger.warning(f"删除essays表约束时出错，可能不存在: {str(e)}")
                
            # 添加新的约束
            batch_op.create_check_constraint(
                'valid_status',
                "status IN ('draft', 'pending', 'processing', 'correcting', 'completed', 'failed', 'archived')"
            )
        
        # 更新corrections表的约束
        logger.info("更新corrections表的约束...")
        # 先删除旧的约束
        with op.batch_alter_table('corrections', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('valid_correction_status', type_='check')
            except Exception as e:
                logger.warning(f"删除corrections表约束时出错，可能不存在: {str(e)}")
                
            # 添加新的约束
            batch_op.create_check_constraint(
                'valid_correction_status',
                "status IN ('pending', 'processing', 'correcting', 'completed', 'failed')"
            )
        
        logger.info("数据库约束更新成功！")
        return True
    except Exception as e:
        logger.error(f"更新数据库约束时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 直接执行SQL来更新约束
    try:
        from app import create_app
        from app.models.db import db
        
        logger.info("正在创建应用实例...")
        app = create_app()
        
        logger.info("正在进入应用上下文...")
        with app.app_context():
            logger.info("正在连接到数据库...")
            
            # 执行直接的SQL命令
            with db.engine.begin() as conn:
                logger.info("正在执行约束更新SQL...")
                
                # essays表更新 - SQLite方式
                try:
                    logger.info("更新essays表约束（SQLite）...")
                    
                    # 获取临时表名
                    temp_table = "__temp_essays"
                    
                    # 检查数据库类型
                    is_sqlite = 'sqlite' in db.engine.url.drivername
                    
                    if is_sqlite:
                        # 1. 创建临时表
                        conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS __temp_essays AS 
                        SELECT * FROM essays
                        """))
                        
                        # 2. 删除原表
                        conn.execute(text("DROP TABLE essays"))
                        
                        # 3. 创建新表（带有新约束）
                        conn.execute(text("""
                        CREATE TABLE essays (
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                            title VARCHAR(200) NOT NULL,
                            content TEXT NOT NULL,
                            word_count INTEGER,
                            user_id INTEGER NOT NULL,
                            author_name VARCHAR(100),
                            status VARCHAR(20),
                            score FLOAT,
                            corrected_at DATETIME,
                            error_message TEXT,
                            grade VARCHAR(50),
                            source_type VARCHAR(20) NOT NULL,
                            corrected_content TEXT,
                            comments TEXT,
                            error_analysis JSON,
                            improvement_suggestions TEXT,
                            ai_score FLOAT,
                            ai_comments TEXT,
                            ai_analysis JSON,
                            view_count INTEGER,
                            like_count INTEGER,
                            comment_count INTEGER,
                            correction_count INTEGER,
                            is_public BOOLEAN,
                            is_deleted BOOLEAN,
                            created_at DATETIME,
                            updated_at DATETIME,
                            CONSTRAINT valid_source_type CHECK (source_type IN ('text', 'paste', 'upload', 'api')),
                            CONSTRAINT valid_status CHECK (status IN ('draft', 'pending', 'processing', 'correcting', 'completed', 'failed', 'archived')),
                            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                        )
                        """))
                        
                        # 4. 复制数据
                        conn.execute(text("INSERT INTO essays SELECT * FROM __temp_essays"))
                        
                        # 5. 删除临时表
                        conn.execute(text("DROP TABLE __temp_essays"))
                        
                        logger.info("essays表约束已更新（SQLite方式）")
                    else:
                        # 对于其他数据库，例如PostgreSQL或MySQL
                        logger.warning("非SQLite数据库，尝试直接更新约束")
                        conn.execute(text("ALTER TABLE essays DROP CONSTRAINT IF EXISTS valid_status"))
                        conn.execute(text("ALTER TABLE essays ADD CONSTRAINT valid_status CHECK (status IN ('draft', 'pending', 'processing', 'correcting', 'completed', 'failed', 'archived'))"))
                        
                except Exception as e:
                    logger.error(f"更新essays表约束时出错: {str(e)}")
                
                # corrections表更新 - SQLite方式
                try:
                    logger.info("更新corrections表约束（SQLite）...")
                    
                    if is_sqlite:
                        # 1. 创建临时表
                        conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS __temp_corrections AS 
                        SELECT * FROM corrections
                        """))
                        
                        # 2. 删除原表
                        conn.execute(text("DROP TABLE corrections"))
                        
                        # 3. 创建新表（带有新约束）
                        conn.execute(text("""
                        CREATE TABLE corrections (
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                            essay_id INTEGER NOT NULL,
                            corrector_id INTEGER,
                            type VARCHAR(20) NOT NULL,
                            content TEXT,
                            score FLOAT,
                            comments TEXT,
                            error_analysis JSON,
                            improvement_suggestions TEXT,
                            extra_data JSON,
                            status VARCHAR(20) NOT NULL,
                            results JSON,
                            task_id VARCHAR(36),
                            error_message TEXT,
                            retry_count INTEGER,
                            created_at DATETIME,
                            updated_at DATETIME,
                            completed_at DATETIME,
                            is_deleted BOOLEAN NOT NULL,
                            CONSTRAINT valid_correction_type CHECK (type IN ('ai', 'human')),
                            CONSTRAINT valid_correction_status CHECK (status IN ('pending', 'processing', 'correcting', 'completed', 'failed')),
                            FOREIGN KEY(corrector_id) REFERENCES users (id) ON DELETE SET NULL,
                            FOREIGN KEY(essay_id) REFERENCES essays (id) ON DELETE CASCADE,
                            UNIQUE (task_id)
                        )
                        """))
                        
                        # 4. 复制数据
                        conn.execute(text("INSERT INTO corrections SELECT * FROM __temp_corrections"))
                        
                        # 5. 删除临时表
                        conn.execute(text("DROP TABLE __temp_corrections"))
                        
                        logger.info("corrections表约束已更新（SQLite方式）")
                    else:
                        # 对于其他数据库，例如PostgreSQL或MySQL
                        logger.warning("非SQLite数据库，尝试直接更新约束")
                        conn.execute(text("ALTER TABLE corrections DROP CONSTRAINT IF EXISTS valid_correction_status"))
                        conn.execute(text("ALTER TABLE corrections ADD CONSTRAINT valid_correction_status CHECK (status IN ('pending', 'processing', 'correcting', 'completed', 'failed'))"))
                        
                except Exception as e:
                    logger.error(f"更新corrections表约束时出错: {str(e)}")
            
            logger.info("所有约束更新完成")
            
    except Exception as e:
        logger.error(f"执行脚本时出错: {str(e)}")
        sys.exit(1)
    
    sys.exit(0) 