# 开发规范与工具

本目录包含了项目开发规范和相关工具，旨在提高代码质量、减少常见错误（如缩进问题）并统一开发风格。

## 文件说明

### 规范文档

- **[python_coding_standards.md](python_coding_standards.md)** - Python编码规范，包含代码风格、命名规范、注释规范、异常处理等标准。
- **[setup_guide.md](setup_guide.md)** - 开发环境设置指南，介绍如何配置一致的开发环境，安装并设置相关工具。

### 工具脚本

- **[syntax_checker.py](syntax_checker.py)** - 语法检查工具，用于检查项目中的缩进和try-except结构问题。
  ```bash
  python rules/syntax_checker.py [项目路径] [排除目录(可选)]
  ```

- **[auto_fix.py](auto_fix.py)** - 自动修复工具，用于自动修复项目中的缩进和try-except结构问题。
  ```bash
  python rules/auto_fix.py [项目路径] [排除目录(可选)]
  ```

## 配置文件

- **[../.editorconfig](../.editorconfig)** - 编辑器配置文件，确保不同IDE下的编辑器设置一致，特别是缩进设置。

## 使用建议

1. **新开发者入职流程**:
   - 阅读 `python_coding_standards.md` 了解项目编码规范
   - 按照 `setup_guide.md` 设置开发环境
   - 安装编辑器插件支持 `.editorconfig`

2. **日常开发流程**:
   - 提交代码前运行 `syntax_checker.py` 检查语法问题
   - 如发现问题，使用 `auto_fix.py` 自动修复

3. **定期维护**:
   - 每周运行一次 `syntax_checker.py` 检查整个项目
   - 在大型合并后运行检查和修复脚本

## 常见问题

### 缩进问题

缩进问题是Python中最常见的问题之一，特别是在大型项目中。遵循以下建议可以减少缩进问题:

1. 始终使用4个空格作为缩进单位，不要使用Tab
2. 启用编辑器的"显示空白字符"功能
3. 使用支持EditorConfig的编辑器

### Try-Except结构

Python中的try-except结构必须完整，每个try必须有对应的except或finally语句。常见错误包括:

1. 遗漏except或finally语句
2. 缩进不正确导致except语句不与try关联

使用 `syntax_checker.py` 可以检测这些问题，使用 `auto_fix.py` 可以自动修复。 