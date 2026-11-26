# CURRENT — 当前进度快照

> 一屏内说清"现在做到哪了、下一步做什么"。**每个功能完成后覆写本文件**（不是追加）。
> 最后更新：2026-11-26

## 当前里程碑

**M1 数据管道：清洗与切分** —— 进行中（下一步开始）

## 已完成

- [x] 项目命名 NexusRAG，GitHub 仓库创建
- [x] 文档体系：AGENTS / ROADMAP / CHARTER / CURRENT / JOURNAL / DECISIONS / INTERVIEW_QA
- [x] .gitignore / .env.example / data/README
- [x] 首次提交 + push
- [x] 补充 ROADMAP（项目兼学习总目录）
- [x] **数据抓取完成**：1000 份药品说明书（化学药+中成药 500 / 中药材 500），
      100% 解析成功、无重复、结构完整（平均正文 1062 字 / 213 字）

## 下一步（按顺序）

- [ ] M1-1 写清洗+切分脚本：两类字段统一 schema → 按章节切成卡片 → `data/processed/chunks.jsonl`
- [ ] M1-2 生成评测集初稿 `data/eval/medical_qa_dev.jsonl`（自动抽取，人工再修正）
- [ ] 技术选型默认档：Chroma + bge-m3 + DeepSeek（记 DECISIONS）

## 阻塞 / 待办

- 无

## 备注

- 数据字段差异：化学药有"适应症/成分/用法用量/禁忌"等标准说明书字段；
  中药材有"功效作用/植物学信息/加工炮制/临床应用"。同义字段（适应症≈适应病症、
  主要功效≈功效作用）切分前需统一。
- 学习地图见 `docs/ROADMAP.md`（当前应停在 M1）。
- 代理为 socks5://127.0.0.1:7897；git push 走 socks5h 配置。
