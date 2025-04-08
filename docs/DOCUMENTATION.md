# 项目文档索引

## 文档结构

```
docs/
├── DOCUMENTATION.md         # 本文件：文档索引
├── CODE_MODIFICATION_GUIDE.md   # 代码修改指南
└── guides/                 # 其他指南文档
    ├── DEPLOYMENT.md      # 部署指南
    ├── DEVELOPMENT.md     # 开发指南
    └── TESTING.md        # 测试指南
```

## 文档说明

### 1. 代码修改指南 (CODE_MODIFICATION_GUIDE.md)

[代码修改指南](CODE_MODIFICATION_GUIDE.md)是一个综合性文档，用于指导开发团队进行系统性的代码修改。它包含：

1. 修改原则
2. 全局分析方法
3. 执行步骤
4. 最佳实践
5. 实际示例

### 2. 开发指南 (guides/DEVELOPMENT.md)

开发指南包含项目的开发规范、环境设置和工作流程说明。

### 3. 部署指南 (guides/DEPLOYMENT.md)

部署指南详细说明了项目的部署步骤和注意事项。

### 4. 测试指南 (guides/TESTING.md)

测试指南包含单元测试、集成测试和端到端测试的说明。

## 使用说明

### 文档使用场景

不同角色应该关注的文档：

- 开发人员
  - CODE_MODIFICATION_GUIDE.md
  - DEVELOPMENT.md
  - TESTING.md
  
- 运维人员
  - DEPLOYMENT.md
  - 监控和日志部分
  
- 项目管理人员
  - DOCUMENTATION.md（本文档）
  - 各指南的概述部分

### 文档维护

本文档库应该随着项目的发展而更新。如果你发现：

- 新的最佳实践
- 常见问题
- 有用的工具
- 改进建议

请通过以下方式贡献：

1. 提交Issue报告问题
2. 提交PR改进文档
3. 分享使用经验

## 文档规范

### 1. 文件命名
- 使用大写字母和下划线
- 使用.md后缀
- 使用有意义的名称

### 2. 文档格式
- 使用Markdown格式
- 包含清晰的标题层级
- 使用代码块展示示例
- 包含适当的链接引用

### 3. 更新维护
- 定期审查和更新
- 记录重要变更
- 保持版本一致性

## 版本控制

所有文档都在Git版本控制下，遵循与代码相同的版本控制规范。

## 许可

MIT License 