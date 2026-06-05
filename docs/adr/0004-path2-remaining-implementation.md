---
title: "ADR-0004: 路径二剩余功能实现方案"
status: "Accepted"
date: "2026-06-04"
authors: ["架构决策者"]
tags: ["architecture", "decision", "intermediate-concept-layer", "frontend"]
supersedes: ""
superseded_by: ""
---

# ADR-0004: 路径二剩余功能实现方案

## Status

**Accepted**

## Context

中间概念层（路径二）的 `build_relations.py` 已完成 5 步数据流水线（LightRAG 实体提取 → LLM 聚类 → 卡片绑定 → 关系推导 + proof → JSON 输出），但仍存在三个断层：

1. **数据模型断层**：`models.py` 的 `KnowledgeCard` 未定义 `relations` 和 `semantic_profile` 字段，导致 `CardPack.from_dict()` 静默丢弃这两个字段的数据
2. **前端展示断层**：`card-app` 仍渲染旧版「④ 知识接口」（`knowledge_interfaces`），未展示新版「⑤ 关联」（`relations` 径向图）
3. **自动化断层**：`generate_app.py` 不感知关系构建流程，需要手动先跑 `build_relations.py` 再跑 `generate_app.py`

## Decision

采用以下方案一次性消除三个断层：

### 1. 数据模型扩展

在 `KnowledgeCard` 中新增 `relations: List[dict]` 和 `semantic_profile: dict` 字段，保留 `knowledge_interfaces` 后向兼容。

### 2. build_relations.py 重构

- 拆分为模块级 API `async def build_relations(params...)` 和 argparse CLI 入口
- Step 4 LLM 精修 prompt 嵌入卡片数据，**一次调用**顺带生成 `function_tag` + `abstract`

### 3. 前端模板升级

- `card-view.js`：替换 section ④ 为 section ⑤，新增 `formatRelations()` 渲染 SVG 径向图
- `state.js`：默认 `expanded` 添加 `relation: true`
- `style.css`：新增径向图、SVG 连线、关系类型配色样式

### 4. 自动化集成

`generate_app.py` 改为 async，新增 `--build-relations` 参数，import `build_relations()` 并在生成应用前自动执行。

## Consequences

### Positive

- **POS-001**: 一次命令完成全部流程（关系构建 + 应用生成），零手动操作
- **POS-002**: `function_tag` + `abstract` 一次 LLM 调用完成，无需额外 API 成本
- **POS-003**: 前端径向图可视化直观展示卡片关系网络，支持「学一知多」
- **POS-004**: 保留后向兼容，旧版 `knowledge_interfaces` 数据不受影响

### Negative

- **NEG-001**: `generate_app.py` 改为 async 后，CLI 调用需 `asyncio.run()` 包装
- **NEG-002**: 前端径向图仅展示预设关系，暂不支持用户自定义添加
- **NEG-003**: SVG 径向布局在关联卡片数量 > 6 时可能超出容器，需滚动

## Alternatives Considered

### 方案 A：分步手动执行（不集成）

- **ALT-001**: **Description**: `build_relations.py` 和 `generate_app.py` 保持独立，用户手动分步执行
- **ALT-002**: **Rejection Reason**: 增加用户操作负担，容易忘记执行关系构建步骤，导致前端数据缺失

### 方案 B：function_tag + abstract 单独一轮 LLM 调用

- **ALT-003**: **Description**: Step 4 精修结束后，单独跑一轮 LLM 为每张卡片生成 function_tag 和 abstract
- **ALT-004**: **Rejection Reason**: 多一次 API 调用增加成本和延迟，且 Step 4 prompt 已包含所有卡片数据，顺带输出无额外开销

### 方案 C：前端保留旧版知识接口

- **ALT-005**: **Description**: 不修改前端模板，仍使用 `knowledge_interfaces` 列表展示
- **ALT-006**: **Rejection Reason**: 无法展示关系类型、proof 证明链、径向图等增强信息，且与 CONTEXT.md 中「关联已替代知识接口」的术语定义矛盾

## Implementation Notes

- **IMP-001**: `build_relations.py` 的 argparse CLI 入口保持不变，`if __name__ == "__main__"` 分支调用模块函数
- **IMP-002**: `generate_app.py` 的 `--build-relations` 默认不启用，需显式传入
- **IMP-003**: 前端径向图节点点击使用 `selectCard(index)` 跳转，复用现有知识链接逻辑
- **IMP-004**: 执行顺序：models.py → build_relations.py 重构 → 前端模板 → generate_app.py 集成 → 运行

## References

- **REF-001**: [ADR-0003: 卡片唯一标识 + 知识接口结构化引用](file:///c:/Users/12977/Desktop/jiyikapian/docs/adr/0003-card-unique-identifier.md)
- **REF-002**: [中间概念层设计 Spec](file:///c:/Users/12977/Desktop/jiyikapian/docs/spec/2026-06-04-intermediate-concept-layer-design.md)
- **REF-003**: [关系图谱设计 Spec](file:///c:/Users/12977/Desktop/jiyikapian/docs/spec/2026-06-04-relation-graph-design.md)
- **REF-004**: [路径二剩余功能实现方案 Spec](file:///c:/Users/12977/Desktop/jiyikapian/docs/spec/2026-06-04-path2-remaining-implementation.md)