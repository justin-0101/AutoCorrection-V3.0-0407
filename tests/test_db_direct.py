"""
直接测试数据库API，绕过Flask表单
"""
import os
import sys
import time
from datetime import datetime
from sqlalchemy import text

# 确保可以导入应用模块
sys.path.append(os.path.abspath('.'))

# 导入应用相关模块
from app import create_app
from app.models.db import db
from app.models.essay import Essay, EssaySourceType
from app.models.user import User

def test_direct_db_api():
    """直接使用SQLAlchemy API测试数据库操作"""
    print("启动直接数据库API测试...")
    
    # 创建应用实例
    app = create_app()
    
    with app.app_context():
        # 获取一个有效的用户
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("找不到admin用户，测试中止")
            return
        
        print(f"找到用户: ID={user.id}, 用户名={user.username}")
        
        # 测试不同的source_type值
        test_cases = [
            {"value": "paste", "desc": "字符串值'paste'"},
            {"value": EssaySourceType.paste, "desc": "枚举实例EssaySourceType.paste"},
            {"value": "paste ", "desc": "带空格的'paste '"},
            {"value": " PASTE", "desc": "带空格和大写的' PASTE'"},
            # 添加特殊测试用例
            {"value": "paste\u200b", "desc": "带零宽空格的'paste\\u200b'"},  # 零宽空格
            {"value": "paste\n", "desc": "带换行符的'paste\\n'"},  # 换行符
            {"value": "paste\t", "desc": "带制表符的'paste\\t'"},  # 制表符
        ]
        
        results = []
        
        for idx, test in enumerate(test_cases):
            try:
                title = f"测试{idx+1}: {test['desc']}"
                print(f"\n开始 {title}")
                
                # 创建Essay对象
                essay = Essay(
                    title=title,
                    content=f"这是测试内容 {idx+1}，测试source_type值: {test['value']}",
                    user_id=user.id,
                    status='pending',
                    source_type=test['value']
                )
                
                # 打印创建的对象信息
                print(f"创建Essay对象: title={essay.title}")
                print(f"创建时的source_type: 值={repr(essay.source_type)}, 类型={type(essay.source_type)}")
                
                # 保存到数据库
                db.session.add(essay)
                db.session.commit()
                
                # 重新从数据库加载，验证值
                db.session.refresh(essay)
                
                print(f"保存后ID: {essay.id}")
                print(f"保存后source_type: 值={repr(essay.source_type)}, 类型={type(essay.source_type)}")
                
                # 使用原生SQL查询，确保数据库中的实际值
                raw_value = db.session.execute(text(f"SELECT source_type FROM essays WHERE id={essay.id}")).scalar()
                print(f"数据库中的原始值: {repr(raw_value)}")
                
                # 检查字符编码
                print(f"字符编码分析: {' '.join([f'U+{ord(c):04X}' for c in raw_value])}")
                
                success = raw_value == 'paste'
                result = {
                    "id": essay.id,
                    "input": test['value'],
                    "output": raw_value,
                    "success": success
                }
                results.append(result)
                
                print(f"测试结果: {'✅ 成功' if success else '❌ 失败'}")
                
            except Exception as e:
                print(f"测试过程中出错: {e}")
                results.append({
                    "input": test['value'],
                    "error": str(e),
                    "success": False
                })
        
        # 总结测试结果
        print("\n====== 测试结果汇总 ======")
        success_count = sum(1 for r in results if r.get('success', False))
        print(f"总共 {len(results)} 测试, {success_count} 成功, {len(results) - success_count} 失败")
        
        for idx, result in enumerate(results):
            status = "✅ 成功" if result.get('success', False) else "❌ 失败"
            if 'error' in result:
                details = f"错误: {result['error']}"
            else:
                details = f"输入: {repr(result['input'])}, 输出: {repr(result['output'])}"
            
            print(f"测试 {idx+1}: {status} - {details}")
        
        # 尝试直接通过POST数据创建一个模拟表单提交
        print("\n\n测试模拟表单提交...")
        try:
            from flask import current_app
            from werkzeug.datastructures import MultiDict
            
            # 模拟表单数据
            form_data = MultiDict([
                ('subject', '模拟表单测试'),
                ('article', '这是模拟表单提交的测试内容'),
                ('source_type', 'paste')  # 明确设置source_type
            ])
            
            # 打印表单数据
            print(f"表单数据: {form_data}")
            print(f"表单中的source_type: {repr(form_data.get('source_type'))}")
            
            # 创建Essay对象的方式与路由处理相同
            source_type = form_data.get('source_type', '')
            print(f"获取的source_type: {repr(source_type)}")
            
            if source_type:
                # 清理并转小写
                original_value = source_type
                source_type = source_type.strip().lower()
                print(f"清理后的source_type: {repr(source_type)}")
            
            source_type_to_use = source_type or "paste"
            print(f"最终使用的source_type: {repr(source_type_to_use)}")
            
            essay = Essay(
                title=form_data.get('subject', '无标题'),
                content=form_data.get('article', ''),
                user_id=user.id,
                status='pending',
                source_type=source_type_to_use
            )
            
            print(f"创建的Essay对象source_type: {repr(essay.source_type)}")
            
            db.session.add(essay)
            db.session.commit()
            
            # 验证保存后的值
            db.session.refresh(essay)
            print(f"保存后的essay.id: {essay.id}")
            print(f"保存后的essay.source_type: {repr(essay.source_type)}")
            
            # 直接查询数据库
            raw_value = db.session.execute(text(f"SELECT source_type FROM essays WHERE id={essay.id}")).scalar()
            print(f"数据库中的原始值: {repr(raw_value)}")
            
            if raw_value == 'paste':
                print("✅ 模拟表单测试成功")
            else:
                print(f"❌ 模拟表单测试失败: 期望'paste'，实际为{repr(raw_value)}")
                
        except Exception as e:
            print(f"模拟表单测试出错: {e}")

if __name__ == "__main__":
    test_direct_db_api() 