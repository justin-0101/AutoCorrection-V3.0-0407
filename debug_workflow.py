import logging
from fix_workflow import (
    check_database_connection,
    check_redis_connection,
    check_ai_service,
    check_essay_processing,
    fix_essay_status
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("workflow_debug")

def run_diagnostic():
    """运行诊断"""
    results = {
        "数据库连接": check_database_connection(),
        "Redis连接": check_redis_connection(),
        "AI服务": check_ai_service(),
        "作文处理": check_essay_processing()
    }
    
    print("\n=== 系统诊断结果 ===")
    for component, status in results.items():
        status_text = "正常 ✓" if status else "异常 ✗"
        print(f"{component}: {status_text}")
    
    return all(results.values())

if __name__ == "__main__":
    print("开始系统诊断...\n")
    if run_diagnostic():
        print("\n诊断完成：系统各组件工作正常")
    else:
        print("\n诊断完成：发现系统异常")