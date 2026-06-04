# 知识卡包 — Understanding-Memory Assistant

**将学习材料从"死记硬背"转化为"理解型记忆"的学习加速器。**

本项目是一个基于 AI Agent 的知识卡片生成系统。上传教材、课堂笔记、录音文字版等学习材料，自动提取知识点、生成理解路径卡片和记忆技巧，并生成可交互的学习应用。

## 核心能力

### AI 技能（.agents/skills/）

| Skill | 职责 |
|:---|:---|
| **understanding-memory** | 主编排器：管理从文件预处理到卡包输出的完整流水线 |
| **type-diagnoser** | 诊断知识点内容类型（逻辑序列/机制机理/结构模型/概念辨析），驱动后续策略 |
| **card-generator** | 根据内容类型，按对应策略生成理解路径卡片（含因果推演、比喻锚定等） |
| **memory-techniques** | 根据内容类型，生成针对性记忆技巧（关键词、口诀、层级图、对比表） |
| **learning-app** | 生成可交互的 HTML 学习应用（支持学习/背诵/复习/概念重组/概念填空模式） |
| **knowledge-extractor** | 从教材文本中自动提取知识点标题清单 |
| **transcript-processor** | 处理录音文字版、课堂笔记等非结构化文本 |

### 卡片形态

每张知识卡片包含：

- **内容类型标签**（颜色编码：蓝=逻辑序列 / 紫=机制机理 / 绿=结构模型 / 橙=概念辨析）
- **答案**（考试默写内容）
- **理解路径**（核心原理 → 分解理解 → 典型判断情境 → 判断链）
- **记忆技巧**（关键词 + 口诀/类比/意象 + 层级图 + 对比表）
- **知识接口**（与其他知识点的关联）

## 快速开始

### 系统要求

- Windows/Mac/Linux
- Python 3.9+
- Trae IDE（或兼容的 Claude API 环境）

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/jiyikapian.git
cd jiyikapian

# 2. Windows — 运行初始化脚本
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 3. 或手动安装依赖
pip install -r scripts\requirements.txt
```

### 使用方法

1. 将学习材料（PDF/DOCX/TXT/MD）放入 `input/参考资料/`
2. 可选：将考点大纲放入 `input/大纲/`
3. 在 Trae IDE 中触发 `understanding-memory` Skill
4. 按提示选择答案来源和确认知识点清单
5. 自动生成知识卡包（JSON + Markdown + HTML 学习应用）

### 生成的学习应用

卡包完成后，在 `output/card-app/` 目录下找到生成的学习应用，直接用浏览器打开 `index.html` 即可使用：

- **📖 学习**：浏览卡片，查看理解路径和记忆技巧
- **🎴 背诵**：翻转卡片模式 + 间隔重复复习
- **📅 复习**：根据记忆曲线安排复习计划
- **🔀 概念重组**：拖拽排序，检验是否理解顺序关系
- **✏️ 概念填空**：填写关键术语，检验记忆

## 项目结构

```
jiyikapian/
├── .agents/
│   └── skills/           # AI Agent 技能
│       ├── understanding-memory/   # 主编排器
│       ├── type-diagnoser/         # 内容类型诊断
│       ├── card-generator/         # 理解路径生成
│       ├── memory-techniques/      # 记忆技巧生成
│       ├── learning-app/           # 学习应用生成
│       ├── knowledge-extractor/    # 知识点提取
│       └── transcript-processor/   # 笔记预处理
├── scripts/              # Python 后端核心
│   ├── card_generator.py # 卡片生成引擎
│   ├── models.py         # 数据模型定义
│   ├── knowledge_store.py# 持久化存储
│   ├── validator.py      # 卡片校验
│   └── setup.ps1         # 初始化脚本
├── input/                # 用户放置学习材料（Git 忽略内容）
│   ├── 参考资料/
│   └── 大纲/
├── output/               # 自动生成的产物
│   ├── card-app/         # 可交互学习应用（HTML）
│   ├── json/             # 卡包 JSON
│   └── markdown/         # 卡包 Markdown
├── docs/                 # 设计文档与架构决策
├── CONTEXT.md            # 领域模型（驱动 AI 行为）
└── LICENSE               # MIT
```

## 内容类型框架

本项目采用四类内容类型驱动理解和记忆策略：

| 类型 | 颜色 | 理解策略 | 记忆策略 |
|:---|:---|:---|:---|
| **A 逻辑序列** | 🟦 蓝色 | 因果推演 + 分组压缩 + 逻辑轴归纳 | 顺序联想口诀 |
| **B 机制/机理** | 🟪 紫色 | 比喻锚定 + 层级图 + 概念对比 | 核心类比 + 因果路径 |
| **C 结构/模型** | 🟩 绿色 | 整体意象 + 逐一追问 + 内部接口图 | 一句话意象 |
| **D 概念辨析** | 🟧 橙色 | 分叉对比 + 场景代入 + 区分口诀 | 区分口诀 + 对比表 |

## 技术栈

- **AI Agent**：Trae IDE + Claude 模型
- **后端**：Python 3（pdfplumber, python-docx）
- **前端**：原生 HTML/CSS/JavaScript（无需构建工具）
- **文档**：Markdown + Mermaid 图表

## 许可

MIT License

Copyright (c) 2026 Understanding-Assistant