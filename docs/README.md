# MoAgent 完整文档索引

欢迎使用 MoAgent 文档！本文档包含项目介绍、架构分析、模块使用等完整内容。

## 📚 文档导航

### 🚀 快速开始

1. **[README.md](../README.md)** - 项目概述和快速入门
   - 项目简介
   - 核心特性
   - 安装指南
   - 基础使用

2. **[QUICKSTART.md](../QUICKSTART.md)** - 5分钟快速开始指南
   - 环境配置
   - 第一个爬虫
   - 常见问题

3. **[INSTALL.md](../INSTALL.md)** - 详细安装说明
   - 所有安装方法
   - 配置说明
   - 验证安装

### 📖 项目文档

4. **[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)** - 项目结构详解
   - 目录结构
   - 文件说明
   - 命名规范
   - 开发工作流

5. **[PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md)** - 项目深度分析
   - **背景与出发点**
     - 问题陈述
     - 解决方案
     - 项目目标
     - 可行性分析
   - **技术架构**
     - 整体架构
     - 核心技术选型
     - 数据流详解
     - 性能优化
   - **模块使用**
     - 爬虫模块
     - 解析器模块
     - 存储模块
     - 配置系统

6. **[AGENTS_ARCHITECTURE.md](../AGENTS_ARCHITECTURE.md)** - Agent系统架构
   - Agent系统概述
   - Coordinator Agent
   - RAG Coordinator
   - Multi-Agent System
   - Pattern Generator
   - 使用示例

### 🔧 技术指南

7. **[CRAWLER_GUIDE.md](CRAWLER_GUIDE.md)** - 爬虫模块完整指南
   - 爬虫架构概述
   - **列表爬虫**
     - HTML列表爬虫
     - 动态列表爬虫
     - RSS列表爬虫
     - LLM列表爬虫
     - 混合列表爬虫
   - **内容爬虫**
     - 模式内容爬虫
     - LLM内容爬虫
     - 混合内容爬虫
   - 爬虫工厂模式
   - 高级配置
   - 性能优化
   - 实战案例

8. **[PARSER_GUIDE.md](PARSER_GUIDE.md)** - 解析器模块完整指南
   - 解析器架构
   - **通用解析器 (GenericParser)**
     - 基础使用
     - 高级选择器
     - 数据清洗
     - 字段验证
   - **LLM解析器 (LLMParser)**
     - 工作原理
     - 自定义提示词
     - 批量解析
   - **混合解析器 (HybridParser)**
     - 智能降级
     - 策略配置
   - 自定义解析器
   - 模式系统
   - 性能优化

### 📋 参考文档

9. **[CONTRIBUTING.md](../CONTRIBUTING.md)** - 贡献指南
   - 开发工作流
   - 代码规范
   - 测试指南
   - Pull Request流程

10. **[CHANGELOG.md](../CHANGELOG.md)** - 版本更新日志
    - 版本历史
    - 新功能
    - Bug修复
    - 破坏性变更

---

## 🎯 按角色查看文档

### 👨‍💻 开发者

必读文档:
1. [README.md](../README.md) - 了解项目
2. [INSTALL.md](../INSTALL.md) - 安装配置
3. [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) - 深度理解架构
4. [CRAWLER_GUIDE.md](CRAWLER_GUIDE.md) - 使用爬虫
5. [PARSER_GUIDE.md](PARSER_GUIDE.md) - 使用解析器

### 🔬 研究者

必读文档:
1. [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) - 技术方案和可行性
2. [AGENTS_ARCHITECTURE.md](../AGENTS_ARCHITECTURE.md) - Agent系统
3. [README.md](../README.md) - 核心特性

### 🌱 新手

必读文档:
1. [README.md](../README.md) - 项目介绍
2. [QUICKSTART.md](../QUICKSTART.md) - 快速上手
3. [CRAWLER_GUIDE.md](CRAWLER_GUIDE.md) - 爬虫使用
4. [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - 代码结构

### 🤝 贡献者

必读文档:
1. [CONTRIBUTING.md](../CONTRIBUTING.md) - 贡献流程
2. [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - 代码组织
3. [AGENTS_ARCHITECTURE.md](../AGENTS_ARCHITECTURE.md) - 架构设计

---

## 📖 阅读顺序建议

### 初学者路径

```
1. README.md (了解项目)
   ↓
2. QUICKSTART.md (快速上手)
   ↓
3. CRAWLER_GUIDE.md (学习爬虫)
   ↓
4. PARSER_GUIDE.md (学习解析)
   ↓
5. PROJECT_ANALYSIS.md (深入理解)
```

### 进阶路径

```
1. PROJECT_ANALYSIS.md (理解设计)
   ↓
2. AGENTS_ARCHITECTURE.md (理解Agent)
   ↓
3. CRAWLER_GUIDE.md (高级用法)
   ↓
4. PARSER_GUIDE.md (高级用法)
   ↓
5. CONTRIBUTING.md (参与开发)
```

### 研究路径

```
1. PROJECT_ANALYSIS.md (技术分析)
   ↓
2. AGENTS_ARCHITECTURE.md (Agent系统)
   ↓
3. 源代码 (实现细节)
```

---

## 🔍 按主题查找

### 核心概念

- [项目背景](PROJECT_ANALYSIS.md#1-项目背景与出发点)
- [整体架构](PROJECT_ANALYSIS.md#2-技术架构详解)
- [数据流](PROJECT_ANALYSIS.md#2.3-数据流详解)
- [Agent系统](../AGENTS_ARCHITECTURE.md#overview)

### 爬虫相关

- [爬虫架构](CRAWLER_GUIDE.md#1-爬虫架构概述)
- [列表爬虫](CRAWLER_GUIDE.md#2-列表爬虫详解)
- [内容爬虫](CRAWLER_GUIDE.md#3-内容爬虫详解)
- [爬虫工厂](CRAWLER_GUIDE.md#4-爬虫工厂模式)
- [性能优化](CRAWLER_GUIDE.md#6-性能优化)

### 解析器相关

- [解析器架构](PARSER_GUIDE.md#1-解析器架构)
- [通用解析器](PARSER_GUIDE.md#2-通用解析器-genericparser)
- [LLM解析器](PARSER_GUIDE.md#3-llm解析器-llmparser)
- [混合解析器](PARSER_GUIDE.md#4-混合解析器-hybridparser)
- [模式系统](PARSER_GUIDE.md#6-模式系统)

### 技术实现

- [LangGraph工作流](PROJECT_ANALYSIS.md#2.2.1-langgraph---工作流编排)
- [LLM集成](PROJECT_ANALYSIS.md#2.2.2-llm集成---openai--anthropic)
- [RAG系统](PROJECT_ANALYSIS.md#2.2.3-rag系统---chromadb)
- [多智能体](PROJECT_ANALYSIS.md#2.2.4-多智能体系统)

### 最佳实践

- [爬虫最佳实践](CRAWLER_GUIDE.md#9-最佳实践)
- [解析器最佳实践](PARSER_GUIDE.md#9-最佳实践)
- [性能优化](PROJECT_ANALYSIS.md#2.4-性能优化策略)

---

## 🛠️ 快速参考

### 常用命令

```bash
# 安装
pip install -e .

# 运行
python -m moagent

# 测试
pytest

# 代码检查
make lint
make format
```

### 配置示例

```yaml
# configs/user_config.yaml
target_url: "https://example.com"
crawl_mode: "auto"
parser_mode: "hybrid"
llm_provider: "openai"
llm_model: "gpt-4o-mini"
```

### 代码示例

```python
from moagent import Config, run_agent

config = Config(
    target_url="https://example.com/news",
    crawl_mode="auto"
)

result = run_agent(config)
```

---

## 📝 文档状态

| 文档 | 状态 | 最后更新 |
|------|------|----------|
| README.md | ✅ 完成 | 2025-01-04 |
| QUICKSTART.md | ✅ 完成 | 2025-01-04 |
| INSTALL.md | ✅ 完成 | 2025-01-04 |
| PROJECT_STRUCTURE.md | ✅ 完成 | 2025-01-04 |
| PROJECT_ANALYSIS.md | ✅ 完成 | 2025-01-04 |
| AGENTS_ARCHITECTURE.md | ✅ 完成 | 2025-01-04 |
| CRAWLER_GUIDE.md | ✅ 完成 | 2025-01-04 |
| PARSER_GUIDE.md | ✅ 完成 | 2025-01-04 |
| CONTRIBUTING.md | ✅ 完成 | 2025-01-04 |
| CHANGELOG.md | ✅ 完成 | 2025-01-04 |

---

## 🔗 外部资源

- **GitHub**: [https://github.com/Lineance/Moagent](https://github.com/Lineance/Moagent)
- **Issues**: [https://github.com/Lineance/Moagent/issues](https://github.com/Lineance/Moagent/issues)
- **Discussions**: [https://github.com/Lineance/Moagent/discussions](https://github.com/Lineance/Moagent/discussions)

---

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE)

---

## 🤝 贡献文档

欢迎改进文档！

1. Fork 项目
2. 编辑文档
3. 提交 Pull Request

文档改进建议:
- 修正错误
- 添加示例
- 补充说明
- 翻译文档

---

**维护者**: MoAgent Team
**最后更新**: 2025-01-04
**文档版本**: v1.0
