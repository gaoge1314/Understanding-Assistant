# 卡牌结构重构设计文档（v4 更新）

> 日期：2026-06-03
> 状态：设计稿（待审批）
> 对应设计讨论：Brainstorming Session 2026-06-03

## 一、概述

### 1.1 动机

基于现有"理解路径记忆助手"的使用反馈，发现两个关键缺陷：

1. **卡牌顺序不可调**：暂时搁置，后续 HTML 生成时通过跨卡链接解决
2. **卡牌结构需要重组**：将单张卡片的内容按"学习→记忆→关联"的认知流程重新组织

### 1.2 新卡牌结构

```
每张卡牌的内容按以下顺序排列：

① 答案（考试默写）
   └─ 学生需要直接背诵并在考试中默写的内容
   └─ 来源：用户指定 / AI从资料提取 / AI自动生成

② 理解路径（现有内容重组）
   ├─ 核心原理
   ├─ 分解理解
   └─ 典型判断情境（题目 + 判断链）

③ 记忆技巧（★ 新增）
   ├─ 关键词（记忆锚点列表）
   ├─ 层级关系（Mermaid flowchart，可选）
   └─ 对比表格（Markdown 表格，可选）

④ 与其他知识的关键接口（移至末尾）
   └─ 知识点间的关系链接
```

### 1.3 第一阶段范围

- **做**：重新设计数据模型 + 调整输出顺序 + 新增记忆技巧子 Skill + 新增预处理模块
- **不做**：卡牌顺序拖拽交互、HTML 导出（留到后续阶段）

---

## 二、架构设计

### 2.1 新的模块架构

```
understanding-memory (主编排器)
│
├── card-generator (现有，修改)
│   └─ 输出格式增加 answer、answer_source、judgment_conclusion 字段
│
├── memory-techniques ★ 新增子 Skill
│   ├─ 关键词提取
│   ├─ 层级关系生成
│   └─ 对比表格生成
│
└── card_generator.py (MCP 工具，修改)
    └─ 输出顺序调整为四段式
```

### 2.3 调用时序

```
                 ┌────────────────────────────────────┐
                 │  understanding-memory               │
                 │  （主编排器）                        │
                 │                                     │
                 │  阶段 0：用户交互                    │
                 │    ├─ 询问文件类型                   │
                 │    ├─ 询问答案来源                   │
                 │    └─ 解析大纲（如有）               │
                 │                                     │
                 │  阶段 1：答案处理                    │
                 │    ├─ 用户指定 → 直接使用            │
                 │    ├─ AI提取 → 扫描资料 → 用户确认   │
                 │    └─ AI生成 → 标记待 card-generator │
                 │                                     │
                 │  阶段 2：知识提取                    │
                 │    └─ knowledge-extractor            │
                 │                                     │
                 │  阶段 3：逐知识点生成（串行流水线）    │
                 │    ① card-generator(title, text,     │
                 │       all_titles, answer)            │
                 │       → 卡片 JSON（不含记忆技巧）     │
                 │    ② memory-techniques(卡片 JSON)    │
                 │       → MemoryTechniques             │
                 │    ③ 编排器组装 → 完整卡片           │
                 │                                     │
                 │  阶段 4：输出                        │
                 │    └─ card_generator.py → MD + JSON  │
                 └────────────────────────────────────┘
```

```
用户上传资料
    │
    ▼
在 understanding-memory/SKILL.md 中交互式询问：
├─ ① 询问文件类型：教材 / 课堂笔记 / 录音转文字 / 考点大纲
├─ ② 询问答案来源：用户指定 / AI从资料提取 / AI自动生成
└─ ③ 解析大纲（如有）
    │
    ▼
原有流程：知识提取 → 卡片生成 → 输出卡包
```

---

## 三、数据模型设计

### 3.1 新增数据结构

```python
@dataclass
class MemoryTechniques:
    """记忆技巧 - AI 自动从卡片内容生成"""
    keywords: List[str]              # 关键词列表，每项含核心术语+记忆提示
    hierarchy: Optional[str]         # Mermaid flowchart TB 层级关系图（可选）
    comparison_tables: List[str]     # Markdown 对比表格列表（可选，每项一个完整表格）

@dataclass
class KnowledgeCard:
    title: str                       # 【知识点】名称

    # ① 答案（★ 新增）
    answer: str                      # 考试默写内容
    answer_source: str               # "user_specified" | "ai_extracted" | "ai_generated"

    # ② 理解路径（现有字段重组，仅调整顺序）
    core_principle: str              # 【核心原理】
    problem_solved: str              # 【它解决了什么问题】
    decomposition: List[str]         # 【分解理解】
    scenario_question: str           # 【典型判断情境】题目
    judgment_chain: List[str]        # 【判断链】推理步骤
    judgment_conclusion: str         # 【判断结论】保留独立字段，与 answer 分开

    # ③ 记忆技巧（★ 新增）
    memory_techniques: MemoryTechniques

    # ④ 知识接口（移至末尾）
    knowledge_interfaces: List[str]  # 【与其他知识的关键接口】
```

### 3.2 MemoryTechniques 生成逻辑

#### 关键词提取（必做）

从 `core_principle`、`decomposition`、`judgment_chain` 中自动提取关键术语，按树形组织：

```
核心术语 → 记忆提示
├─ 派生术语 A → 记忆提示
├─ 派生术语 B → 记忆提示
└─ 易混术语 C → 区分提示
```

#### 层级关系图（条件触发）

当知识点具有明显的分类/组成/层次结构时生成 Mermaid `flowchart TB`。

**触发条件**：
- 知识点包含子分类（如"灾害系统→孕灾环境/致灾因子/承灾体/灾情"）
- 知识点有步骤/阶段划分（如"三阶段/四步骤"）
- 知识点有包含/从属关系

**与 card-generator 中现有流程图的区别**：

| 维度 | card-generator 流程图 | memory-techniques 层级图 |
|:---|:---|:---|
| 目的 | 展示内部结构 | 辅助记忆 |
| 粒度 | 详细完整 | 精简，只保留骨架 |
| 位置 | decomposition 末尾 | 记忆技巧板块 |

#### 对比表格（条件触发）

当知识点存在易混淆概念时生成 Markdown 对比表格。

**触发条件**：
- 知识点本身有"对比"、"区别"、"vs"等关键词
- `knowledge_interfaces` 中指向了相似知识点
- 知识点与其他概念存在"易混淆"关系

**表格结构**：

| 比较维度 | 概念 A | 概念 B |
|---------|--------|--------|
| 根本原因 | ... | ... |
| 表现差异 | ... | ... |
| 导致后果 | ... | ... |

未触发时：`comparison_tables` 为空列表 `[]`，输出中省略该小节。

---

## 四、Markdown 输出格式

### 4.1 新卡片模板

```markdown
---

## 卡片 {n}/{total}：{title}

### ① 答案（考试默写）

{answer}

> 来源：[用户指定 / AI提取 / AI生成]

---

### ② 理解路径

**核心原理**：{core_principle}

**它解决了什么问题**：{problem_solved}

**分解理解**：
- {decomposition_step1}
- {decomposition_step2}
- ...

**典型判断情境**：
**题目**：{scenario_question}

**判断链**：
{judgment_chain_step1}
{judgment_chain_step2}
...

---

### ③ 记忆技巧

**关键词**：
- {keyword1}
- {keyword2}
- ...

**层级关系**：（如有）
```mermaid
flowchart TB
    ...
```

**对比表格**：（如有）
| 维度 | A | B |
|...|...|...|

---

### ④ 与其他知识的关键接口

- → {知识点X}：{关系说明}
- → {知识点Y}：{关系说明}

---
```

### 4.3 文件名更新

| 文件类型 | 旧名称 | 新名称 |
|:---|:---|:---|
| Markdown | `{subject}_理解路径卡包.md` | `{subject}_知识卡包.md` |
| JSON | `{subject}_v{version}.json` | 不变 |

```json
{
  "cards": [
    {
      "title": "灾害系统四要素",
      "answer": "灾害系统由孕灾环境、致灾因子、承灾体和灾情四要素构成",
      "answer_source": "ai_generated",
      "core_principle": "灾害不是一件事，而是一个失效的系统",
      "problem_solved": "破除了天灾=老天爷发怒的迷思",
      "decomposition": ["..."],
      "scenario_question": "...",
      "judgment_chain": ["..."],
      "judgment_conclusion": "构成灾情",
      "memory_techniques": {
        "keywords": [
          "灾害系统 → 三大子系统组成的整体系统",
          "孕灾环境 → 灾害发生的背景条件",
          "致灾因子 → 灾害的直接触发因素"
        ],
        "hierarchy": "```mermaid\nflowchart TB\n    灾害系统 --> 孕灾环境\n    灾害系统 --> 致灾因子\n    灾害系统 --> 承灾体\n```",
        "comparison_tables": []
      },
      "knowledge_interfaces": [
        "→ 灾害动力学：四要素动起来就是动力学",
        "→ 灾害特征：从五个维度给灾害画像"
      ]
    }
  ]
}
```

---

## 五、文件变动清单

### 5.1 新增文件

| # | 文件 | 说明 |
|:---|:---|:---|
| 1 | `.agents/skills/memory-techniques/SKILL.md` | 记忆技巧子 Skill：接收卡片数据，输出 MemoryTechniques |

### 5.2 修改文件

| # | 文件 | 修改内容 |
|:---|:---|:---|
| 1 | `scripts/models.py` | 新增 `MemoryTechniques` 数据类；`KnowledgeCard` 新增 `answer`、`answer_source`、`memory_techniques` 字段；`scenario_answer` → `judgment_conclusion`（改名保留） |
| 2 | `scripts/card_generator.py` | 调整输出顺序为四段式；新增记忆技巧渲染逻辑；校验规则更新：检查 `answer` 非空、`memory_techniques.keywords` 非空 |
| 3 | `scripts/knowledge_store.py` | 适配新字段（`answer`、`answer_source`、`judgment_conclusion`、`memory_techniques`）；旧 JSON 读取时兼容 `scenario_answer` 映射 |
| 4 | `.agents/skills/card-generator/SKILL.md` | 输出格式中增加 `answer`、`answer_source`、`judgment_conclusion` 字段（不含 memory_techniques，由 memory-techniques 子 Skill 补充） |
| 5 | `.agents/skills/understanding-memory/SKILL.md` | 编排流程增加：询问文件类型→询问答案来源→解析大纲→调用 memory-techniques 子 Skill |

### 5.3 字段说明

| 字段 | 状态 | 说明 |
|:---|:---|:---|
| `KnowledgeCard.answer` | **新增** | 考试默写内容，与判断结论独立 |
| `KnowledgeCard.answer_source` | **新增** | 答案来源标注 |
| `KnowledgeCard.judgment_conclusion` | **保留独立** | 原 `scenario_answer`，保持独立不与 answer 合并 |

### 5.4 整合包最终结构

```
jiyikapian/                          ← 用户下载后解压即用
│
├── .agents/
│   └── skills/
│       ├── understanding-memory/     # 主编排器（改）
│       ├── card-generator/           # 卡片生成（改）
│       ├── memory-techniques/        # ★ 新增·记忆技巧
│       ├── knowledge-extractor/      # 知识点提取（不变）
│       └── transcript-processor/     # 转录本处理（不变）
│
├── scripts/
│   ├── __init__.py
│   ├── models.py                     # 数据模型（改）
│   ├── card_generator.py             # 卡片输出（改）
│   ├── knowledge_store.py            # 持久化（改）
│   └── requirements.txt
│
├── input/                            # ★ 用户放置资料的目录
│   ├── 参考资料/                     # 教材、课堂笔记、录音转文字
│   │   └── .gitkeep
│   └── 大纲/                         # 考点大纲文件
│       └── .gitkeep
│
├── output/                           # 运行时自动创建
│   ├── markdown/
│   ├── json/
│   ├── knowledge/
│   └── processed/
│
├── docs/
│   └── README.md                     # ★ 使用说明
│
├── scripts/
│   └── setup.ps1                     # ★ 初始化脚本（创建目录结构 + 安装依赖）
│
└── CONTEXT.md
```

---

## 六、实施计划

### 阶段 1：数据模型 → models.py

添加 `MemoryTechniques` 数据类，修改 `KnowledgeCard`。

### 阶段 2：子 Skill → memory-techniques/SKILL.md

实现关键词/层级图/对比表生成逻辑。

### 阶段 3：修改现有文件

- `card-generator/SKILL.md`：输出格式增加新字段
- `card_generator.py`：输出顺序调整为四段式
- `knowledge_store.py`：适配新字段 + 旧数据兼容
- `understanding-memory/SKILL.md`：编排流程增加预处理和记忆技巧调用

### 阶段 4：整合包打包

- 创建 `input/参考资料/` 和 `input/大纲/` 目录结构
- 编写 `docs/README.md` 使用说明
- 编写 `setup.ps1` 初始化脚本

---

## 七、兼容性考虑

### 7.1 向后兼容

- 旧版本 JSON 数据（`v1`~`v3`）仍然可读，`knowledge_store.py` 读取旧数据时自动将 `scenario_answer` 映射为 `judgment_conclusion`
- 旧版 Markdown 输出格式不变，重新生成时才使用新版格式
- `answer`、`memory_techniques` 等新字段在旧 JSON 中不存在时自动填充空值

### 7.2 增量更新流程

已有卡包增量更新时：
1. 加载旧卡包数据
2. 旧卡包的 `scenario_answer` → 映射到新卡包的 `judgment_conclusion`
3. 旧卡包的 `answer` 字段空值由 AI 在增量生成时补充
4. 新增的 `memory_techniques` 字段由 AI 在增量生成时补充

---

## 八、设计原则检查

| 原则 | 状态 | 说明 |
|:---|:---|:---|
| YAGNI | ✅ | 只做需求中明确提到的四个部分，不做多余的交互功能 |
| 单一职责 | ✅ | memory-techniques 独立为子 Skill，与 card-generator 职责不重叠 |
| 可扩展 | ✅ | 后续可独立修改记忆技巧生成逻辑，不影响卡片核心内容 |
| 用户控制 | ✅ | 用户决定答案来源（指定/提取/生成），决定提供哪些资料 |
| 增量友好 | ✅ | 旧数据兼容读取，新增字段自动填充 |