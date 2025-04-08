import inspect
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def print_essay_model():
    """打印Essay模型的定义"""
    try:
        from app.models.essay import Essay, EssaySourceType
        
        print("=" * 80)
        print("Essay模型定义")
        print("=" * 80)
        print(inspect.getsource(Essay))
        print()
        
        print("EssaySourceType枚举定义")
        print("=" * 80)
        print(inspect.getsource(EssaySourceType))
        print()
        
        # 检查Essay模型属性
        print("Essay模型属性:")
        model_attrs = [attr for attr in dir(Essay) if not attr.startswith('_')]
        for attr in model_attrs:
            if attr not in ['metadata', 'query', 'query_class']:
                print(f"  - {attr}")
        print()
    except ImportError as e:
        print(f"无法导入Essay模型: {e}")
    except Exception as e:
        print(f"获取Essay模型定义时出错: {e}")

def print_route_handler():
    """打印作文提交路由处理函数"""
    try:
        from app.routes.main_routes import correction
        
        print("=" * 80)
        print("作文提交路由处理函数")
        print("=" * 80)
        print(inspect.getsource(correction))
        print()
    except ImportError as e:
        print(f"无法导入路由处理函数: {e}")
    except Exception as e:
        print(f"获取路由处理函数定义时出错: {e}")

def print_essay_creation():
    """打印作文创建代码"""
    try:
        # 读取main_routes.py文件
        with open("app/routes/main_routes.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 查找创建Essay对象的代码
        import re
        essay_creation_patterns = [
            r"essay\s*=\s*Essay\([^)]*\)",
            r"Essay\(\s*title=[^)]*\)",
        ]
        
        print("=" * 80)
        print("Essay对象创建代码片段")
        print("=" * 80)
        
        for pattern in essay_creation_patterns:
            matches = re.findall(pattern, content)
            for i, match in enumerate(matches):
                print(f"创建Essay实例 #{i+1}:")
                print(match)
                print()
    except Exception as e:
        print(f"获取Essay创建代码时出错: {e}")

if __name__ == "__main__":
    print_essay_model()
    print_route_handler()
    print_essay_creation() 