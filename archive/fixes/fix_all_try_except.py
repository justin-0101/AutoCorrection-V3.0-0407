import os
import logging
import re

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def fix_try_except_in_file(file_path):
    """修复文件中的破损的try-except结构"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        fixed_lines = []
        i = 0
        fixed_count = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 查找try语句行，但后面没有正确的缩进代码块
            if re.match(r'(\s*)try\s*:', line):
                indent = re.match(r'(\s*)', line).group(1)
                next_line_index = i + 1
                
                # 查看下一行，检查是否是except语句或缩进不正确
                if (next_line_index < len(lines) and 
                    (re.match(r'(\s*)except', lines[next_line_index]) or 
                     not lines[next_line_index].startswith(indent + '    '))):
                    
                    # 修复try-except结构
                    fixed_lines.append(line)
                    fixed_lines.append(f"{indent}    pass  # 自动修复的空块")
                    fixed_count += 1
                    logger.info(f"在{file_path}的第{i+1}行修复了try块")
                    i += 1
                    continue
            
            fixed_lines.append(line)
            i += 1
        
        # 只有在有修复的情况下才写回文件
        if fixed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            logger.info(f"修复了{file_path}中的{fixed_count}个try-except结构")
            return fixed_count
        return 0
    
    except Exception as e:
        logger.error(f"修复{file_path}时出错: {e}")
        return 0

def scan_and_fix_directory(directory='.'):
    """扫描目录中的所有Python文件并修复try-except结构"""
    total_files = 0
    total_fixed = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_files += 1
                fixed_count = fix_try_except_in_file(file_path)
                total_fixed += fixed_count
    
    logger.info(f"扫描了{total_files}个Python文件，修复了{total_fixed}个try-except结构")
    return total_fixed

if __name__ == "__main__":
    fixed_count = scan_and_fix_directory()
    if fixed_count > 0:
        print(f"成功修复了{fixed_count}个try-except结构！")
    else:
        print("没有发现需要修复的try-except结构。") 