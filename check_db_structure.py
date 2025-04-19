import sqlite3
import os
import json

def main():
    print("===== 数据库结构检查工具 =====")
    
    # 检查数据库文件是否存在
    db_path = 'instance/essay_correction.db'
    if not os.path.exists(db_path):
        print(f"错误: 找不到数据库文件 {db_path}")
        return
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取corrections表的结构
        print("\n检查corrections表结构:")
        cursor.execute("PRAGMA table_info(corrections)")
        columns = cursor.fetchall()
        for column in columns:
            print(f"列名: {column[1]}, 类型: {column[2]}, 是否可为空: {'是' if column[3]==0 else '否'}, 默认值: {column[4]}")
        
        # 检查status字段的唯一值
        print("\n检查status字段的唯一值:")
        try:
            cursor.execute("SELECT DISTINCT status FROM corrections WHERE is_deleted=0")
            statuses = cursor.fetchall()
            if not statuses:
                print("没有找到任何status值")
            else:
                print("status字段的唯一值有:")
                for status in statuses:
                    print(f"- {status[0]}")
        except sqlite3.Error as e:
            print(f"查询status值时出错: {e}")
        
        # 检查模型代码中定义的状态
        print("\n检查essay_id=86的状态:")
        cursor.execute("SELECT id, essay_id, status, created_at, updated_at FROM corrections WHERE essay_id=86 AND is_deleted=0")
        corrections = cursor.fetchall()
        if not corrections:
            print("没有找到essay_id=86的有效记录")
        else:
            for correction in corrections:
                print(f"correction_id={correction[0]}, essay_id={correction[1]}, status={correction[2]}")
                print(f"创建时间: {correction[3]}, 更新时间: {correction[4]}")
        
        # 检查相应的essay表记录
        print("\n检查essays表中id=86的记录状态:")
        cursor.execute("SELECT id, status, created_at, updated_at FROM essays WHERE id=86")
        essay = cursor.fetchone()
        if not essay:
            print("没有找到id=86的essay记录")
        else:
            print(f"essay_id={essay[0]}, status={essay[1]}")
            print(f"创建时间: {essay[2]}, 更新时间: {essay[3]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"数据库操作出错: {e}")
    
    print("\n检查完成。")

if __name__ == "__main__":
    main() 