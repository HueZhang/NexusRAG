# NexusRAG

> 一个模块化、可评测、面向多领域的 **RAG（检索增强生成）中台**。
> 通用核心层 + 可插拔场景接入层 —— 首个落地模板：医疗说明书合规问答。

![status](https://img.shields.io/badge/status-WIP-yellow)
![python](https://img.shields.io/badge/python-3.11-blue)
![license](https://img.shields.io/badge/license-TBD-lightgrey)

---

## 这是什么

NexusRAG 不是"一个 RAG 应用"，而是一个**可以按领域搭建 RAG 流水线的平台**：

- **核心层**只面向接口（LLMProvider / Embedder / Retriever / Reranker / Chunker），
  换模型、换向量库、换行业都是替换实现，核心不动。
- **场景接入层**以"模板"形式插入，贡献专属的解析器、Prompt、评测集。
- **评测贯穿全流程**：检索召回、答案忠实度（防幻觉）、答案相关性都可量化。

> _Nexus = 枢纽 / 连接。它把数据、模型、行业场景连接成一条可复用的流水线。_

## 四层架构（示意）

```
接入层 (Adapters: 医疗说明书 / …)      ← 场景模板
应用层 (Application: 检索→重排→生成→引用)
核心层 (Domain: 只定接口/协议)
基础设施层 (Infrastructure: 具体模型/向量库实现)
        ↑ 数据管道 & 评测贯穿全程
```

## 状态

🚧 早期搭建中。当前进度见 [`docs/CURRENT.md`](docs/CURRENT.md)。
项目定位、里程碑与设计见 [`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)。

## 文档

- [项目章程 PROJECT_CHARTER](docs/PROJECT_CHARTER.md)
- [当前进度 CURRENT](docs/CURRENT.md)
- [开发日志 JOURNAL](docs/JOURNAL.md)
- [关键技术决策 DECISIONS](docs/DECISIONS.md)
- [面试问答 INTERVIEW_QA](docs/INTERVIEW_QA.md)
- [协作契约 AGENTS](AGENTS.md)

## License

TBD
