import sqlite3
import os

def check_latest_essays():
    db_path = os.path.join('instance', 'essay_correction.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查最近的5条记录
        cursor.execute("""
        SELECT id, title, user_id, source_type, status, created_at
        FROM essays
        ORDER BY id DESC
        LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("未找到作文记录")
            return
        
        print("最新的作文记录:")
        print("ID\t标题\t用户ID\tsource_type\t状态\t创建时间")
        print("-" * 80)
        
        for row in rows:
            essay_id, title, user_id, source_type, status, created_at = row
            print(f"{essay_id}\t{title}\t{user_id}\t{source_type}\t{status}\t{created_at}")
        
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_latest_essays() 