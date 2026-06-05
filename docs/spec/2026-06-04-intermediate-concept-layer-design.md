# 中间概念层设计方案

## 概述

在 LightRAG 微观实体（259 个）与知识卡片（24 张）之间插入**中间概念层**，解决实体粒度与卡片粒度不匹配导致的关系推导精度问题。

## 背景问题

| 问题 | 描述 |
|:---|:---|
| **粒度断层** | LightRAG 抽取 259 个微观实体 + 264 条关系，而知识卡片仅 24 张。实体粒度是"热辐射""装置失效"，卡片粒度是"灾害链""Na-tech 事件" |
| **标题匹配瓶颈** | 基于标题的文本匹配仅覆盖 14/24 张卡片。LightRAG 实体名称与卡片标题使用不同术语体系（如"多米诺骨牌" vs "多米诺效应"） |
| **关系质量不足** | 直接依赖 LightRAG 实体关系推导卡片关系时，因粒度断层产生大量噪声和遗漏 |

## 解决方案：三层架构

```
┌─────────────────────────────────────┐
│        Card Layer（卡片层）          │  ← 24 张知识卡片（已知）
│                                      │
│        概念级关联（推导目标）           │
│                                      │
├─────────────────────────────────────┤
│   Intermediate Concept Layer        │  ← 20-30 个 LLM 聚类生成的高层概念
│   （中间概念层，新增）                 │
│                                      │
│        实体→概念映射                   │
│                                      │
├─────────────────────────────────────┤
│    Micro Entity Layer（微观实体层）     │  ← 259 个实体 + 264 条关系（来自 LightRAG）
│                                      │
└─────────────────────────────────────┘
```

**核心思想**：不是让 259 个实体直接绑定到 24 张卡片，而是先让 LLM 将 259 个实体聚类为 20-30 个中间概念（如"能量传递机制""触发条件""阈值效应"），再通过中间概念建立卡片间的关系网络。

---

## 五步流水线

### Step 1：数据准备

**输入**：
- `graph_chunk_entity_relation.graphml` — LightRAG 知识图谱
- `灾害学_v5.json` — 24 张知识卡片

**输出**：
- 实体三元组列表：`(实体A, 关系, 实体B)`，如 `(热辐射, 导致, 装置失效)`
- 卡片标题列表 + 每张卡的现有 `relations` 字段

**处理方式**：
```python
# 伪代码
entities = extract_entities(graphml)       # 259 个实体
triples = extract_triples(graphml)          # 264 条三元组
card_titles = [c["title"] for c in cards]  # 24 个卡片标题
```

### Step 2：LLM 聚类 — 生成中间概念

**输入**：
- 259 个实体名称（含 description）
- 264 条三元组（关系三元组）
- 24 张卡片标题（作为聚类锚点）

**LLM 调用**：DeepSeek v4 flash，`response_format=json_object`

**Prompt 要求**：
- 将 259 个实体聚类为 20-30 个高层概念
- 每个中间概念包含：`name`、`description`、`member_entities`（归属的实体列表）
- 卡片标题作为聚类锚点——概念应尽量与卡片语义对齐
- 输出格式强制 JSON

**输出示例**：
```json
[
  {
    "name": "能量传递机制",
    "description": "描述灾害过程中能量的积累、转化和释放的机制",
    "member_entities": ["热辐射", "冲击波", "动能", "势能", "能量耗散"]
  },
  {
    "name": "触发条件",
    "description": "引发灾害或事故的初始触发因素",
    "member_entities": ["地震", "暴雨", "台风", "人为失误", "设备老化"]
  }
]
```

**中间产物存储**：临时 JSON 文件 `intermediate_concepts.json`

### Step 3：卡片到中间概念的绑定

**策略**：混合方法（Method A → Method B）

#### Method A：基于实体交集（严格匹配）

```
对每张卡片 C：
  提取 C 中出现的实体集合 E_c（从 card JSON 的 answer + decomposition 中提取）
  对每个中间概念 IC：
    计算交集 |E_c ∩ member_entities(IC)|
    如果交集 ≥ 2 个实体 → 绑定 C 到 IC
```

预期绑定率：约 60-70%（部分卡片直接命中）

#### Method B：LLM 绑定（补充未绑定卡片）

对 Method A 未能绑定的剩余卡片，调用 LLM：

```
输入：卡片标题 + 卡片内容（answer, core_principle, decomposition）
      未匹配的中间概念列表
输出：该卡片应绑定的中间概念（0-N 个）
```

### Step 4：关系推导 + 证明链生成

**策略**：规则引擎预分类（Method A）+ LLM 精化与证明撰写（Method B）

#### Method A：规则引擎预分类

```
对每对卡片 (C1, C2)：
  获取绑定的中间概念集 IC1, IC2
  计算共享概念集 shared_IC = IC1 ∩ IC2
  
  如果 shared_IC 非空 → C1 和 C2 存在潜在关系
    关系类型由规则引擎预分类：
      - shared_IC 包含"因果"类概念 → type = "theorize"
      - shared_IC 包含"对比/辨析"类概念 → type = "contrast"
      - default → type = "expand"
```

#### Method B：LLM 精化与证明撰写

对 Method A 产生的每条候选关系，调用 LLM 进行精化和补充证明：

```
输入：
  - 卡片 C1（title + core_principle + answer 摘要）
  - 卡片 C2（title + core_principle + answer 摘要）
  - 共享的中间概念列表
  - 共享的 LightRAG 实体列表
输出：
  - 关系类型（expand/generalize/contrast/theorize/apply/precede/succeed）
  - label（关系描述文本）
  - proof={
      shared_entities: ["实体的名称"],
      intermediate_concepts: ["中间概念的名称"],
      reasoning: "为什么这两张卡片有关系，基于共享实体和概念推导"
    }
```

**proof 字段示例**：
```json
{
  "targetId": "Na-tech事件",
  "type": "theorize",
  "label": "自然灾害触发技术事故是灾害链在化工领域的特例",
  "proof": {
    "shared_entities": ["自然灾害", "技术事故", "连锁反应"],
    "intermediate_concepts": ["触发机制", "链式反应"],
    "reasoning": "灾害链定义了一灾引发多灾的连锁模式，Na-tech事件则是自然灾害触发的技术事故链，两者共享'触发机制'和'链式反应'两个中间概念，构成一般与特殊的关系"
  }
}
```

### Step 5：输出 — 更新卡 JSON

对每张卡片：
1. 新增 `semantic_profile` 字段
2. 增强 `relations` 字段（添加 `proof`）

**semantic_profile** 字段结构：
```json
{
  "title": "灾害链",
  "semantic_profile": {
    "core_terms": ["连锁反应", "因果传递", "并发", "串发"],
    "function_tag": "mechanism_description",
    "abstract": "描述一种灾害引发一系列灾害的连锁现象，分为并发性和串发性两种传递模式"
  },
  "relations": [
    {
      "targetId": "Na-tech事件",
      "type": "theorize",
      "label": "...",
      "proof": {
        "shared_entities": ["自然灾害", "技术事故"],
        "intermediate_concepts": ["触发机制", "链式反应"],
        "reasoning": "..."
      }
    }
  ]
}
```

---

## 数据模型变更

| 字段 | 所属对象 | 类型 | 说明 |
|:---|:---|:---|:---|
| `semantic_profile.core_terms` | Card | string[] | 2-5 个核心术语，提取自卡片回答 |
| `semantic_profile.function_tag` | Card | string | 功能标签：`mechanism_description` / `comparison_analysis` / `process_flow` / `structural_model` / `practical_guideline` |
| `semantic_profile.abstract` | Card | string | 一句话抽象概括（≤50 字） |
| `relations[].proof.shared_entities` | Relation | string[] | 共享的 LightRAG 实体名称列表 |
| `relations[].proof.intermediate_concepts` | Relation | string[] | 共享的中间概念名称列表 |
| `relations[].proof.reasoning` | Relation | string | 关系推导的推理过程 |
| `intermediate_concepts`（临时文件） | N/A | JSON 数组 | 20-30 个中间概念，含 `name`、`description`、`member_entities` |

---

## 设计决策记录

| 决策 | 选项 | 选择 | 理由 |
|:---|:---|:---|:---|
| **输入格式** | 纯实体列表 / 三元组列表 | **三元组列表**（实体A, 关系, 实体B） | 保留 LightRAG 的关系结构，LLM 可以理解实体间的语义连线，聚类质量更高 |
| **LLM 模型** | DeepSeek v3 / DeepSeek v4 flash | **DeepSeek v4 flash** | 成本低、速度快，JSON 输出支持好 |
| **JSON 输出强制** | 可选 / 强制 | **强制**（`response_format=json_object`） | 确保下游 Python 脚本可以直接解析，避免解析错误 |
| **聚类锚点** | 纯实体聚类 / 卡片标题作为锚点 | **卡片标题作为锚点** | 确保中间概念语义对齐卡片体系，减少后续绑定难度 |
| **卡片绑定方式** | 纯 LLM / 纯规则 / **混合** | **混合**（Method A 实体交集 → Method B LLM 补充） | 严格匹配保证可追溯性和稳定性，LLM 补充保证覆盖率 |
| **关系推导方式** | 纯 LLM / 纯规则 / **混合** | **混合**（规则引擎预分类 → LLM 精化 + 证明撰写） | 规则引擎保证基础关系不遗漏，LLM 保证关系质量和 proof 的可解释性 |
| **中间概念数量** | 10-15 / 20-30 / 30-50 | **20-30** | 太少则粒度断层仍大，太多则失去中间层意义 |
| **中间产物存储** | 不存储 / 写入 card JSON / **临时 JSON 文件** | **临时 JSON 文件** | 只在构建时使用，不污染最终的卡片数据结构 |
| **proof 字段** | 仅存推理文本 / 结构化 | **结构化**（shared_entities + intermediate_concepts + reasoning） | 结构化数据可供前端逐项展示"为什么有关联" |

---

## 变更文件清单

| 文件 | 操作 | 说明 |
|:---|:---|:---|
| `scripts/build_relations.py` | **大幅修改** | 新增中间概念层流水线（Step 1-5） |
| `scripts/intermediate_concepts.json` | **新增**（临时） | Step 2 输出的中间概念，构建时生成，不提交 |
| `output/json/灾害学_v5.json` | **修改** | 每张 card 新增 `semantic_profile`，`relations` 增强 `proof` |
| `CONTEXT.md` | **修改** | 已包含新术语（semantic_profile、intermediate_concept、proof） |

---

## 排除范围

- **不改变前端 UI**：proof 字段存储但不渲染（留待后续迭代）
- **不改变卡片核心字段**：title、answer、decomposition、memory_techniques 等不变
- **不修改 LightRAG**：仍只运行一次，输出固化
- **不引入新依赖**：仅使用现有 DeepSeek API + Python 标准库
- **不修改卡片数量**：仍为 24 张，不增