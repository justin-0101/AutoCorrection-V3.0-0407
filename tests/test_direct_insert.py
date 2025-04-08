import sqlite3
from datetime import datetime
import os

def direct_insert_essay():
    """直接通过SQL插入记录，绕过验证逻辑"""
    db_path = os.path.join('instance', 'essay_correction.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取一个有效的用户ID
        cursor.execute("SELECT id FROM users LIMIT 1")
        user_id = cursor.fetchone()[0]
        
        # 获取当前时间
        now = datetime.now().isoformat()
        
        # 执行插入
        cursor.execute("""
        INSERT INTO essays (
            title, content, user_id, status, source_type, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "直接插入的测试作文", 
            "这是通过直接SQL插入的测试内容，绕过模型验证逻辑。", 
            user_id,
            "pending",
            "paste",  # 显式设置为paste类型
            now,
            now
        ))
        
        # 提交事务
        conn.commit()
        
        # 获取插入的ID
        essay_id = cursor.lastrowid
        print(f"成功插入作文记录，ID: {essay_id}, source_type: paste")
        
        # 查询验证
        cursor.execute("SELECT id, title, source_type FROM essays WHERE id = ?", (essay_id,))
        result = cursor.fetchone()
        print(f"查询结果: ID={result[0]}, 标题={result[1]}, source_type={result[2]}")
        
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    direct_insert_essay() 