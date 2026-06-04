# CONTEXT — Understanding-Assistant

## 术语表

| 术语 | 定义 |
|:---|:---|
| **知识卡牌** | 单张知识卡片，由五部分构成：①内容类型标签（颜色编码） ②答案 ③理解路径 ④记忆技巧 ⑤知识接口。内容类型（A/B/C/D/mixed）由诊断 Skill 自动判断，在卡包 JSON 中以 `content_type` 字段存储，前端根据类型渲染不同颜色 |
| **理解路径** | 知识卡牌的第二板块，展示知识的内在逻辑（核心原理、分解理解、典型判断情境） |
| **知识卡包** | 一组知识卡牌的集合，对应一份学习材料 |
| **学习应用** | 由 learning-app Agent 从卡包 JSON 生成的交互式 HTML 应用 |
| **重构** | 用户在右侧栏中"拆散→重组"知识的统称，含多种子模式（概念重组、概念填空、自我解释等） |
| **概念重组** | 重构的子模式之一：将打乱的概念块拖拽到正确逻辑位置，系统比对并反馈 |
| **重构类型** | JSON 字段 `reconstruct_type`，标记卡片适合哪些重构模式（数组）。值：`"reorder"`（平行概念拖拽排序）、`"fill-blank"`（概念填空）、`[]`（不适合任何重构） |
| **概念填空** | 重构的子模式之一：Agent 预生成挖空数据（`blanks` 字段），用户填写关键术语，系统比对反馈 |
| **三视图导航** | 顶部 Tab 切换三个视图：📖 学习（三栏）、🎴 背诵（翻转卡+记忆曲线）、📅 复习（进度概览+字数设置） |
| **背诵模式** | 翻转卡学习，正面标题 → 翻转看答案 → 底部"记得/忘了"反馈，联动记忆曲线 |
| **记忆曲线** | 改良 SM-2 算法：间隔 1→3→7→21→60→180 天，"记得"递进、"忘了"重置到 Level 1 |
| **每日字数** | 用户设每日背诵字数配额（200/500/1000/3000），系统推荐卡片，总字数 ≥90% 且 ≤108% 配额 |
| **今日计划** | 用户每日背诵前的选卡入口，支持"按组选择"和"智能推荐"双模式。选中的卡片自动创建背诵组（"第一组""第二组"...），以组为单位进入背诵视图。背诵组不显示在侧边栏。新建计划时可选择将上一组未完成的卡片纳入新组 |
| **默认组** | 存放所有未分入用户自定义组的卡片，始终存在且不可删除。位于侧边栏分组列表最底部 |
| **提示** | 背诵模式下显示的关键词摘要，取自 `memory_techniques.keywords`，用户可编辑内容和显示数量 |
| **用户笔记** | 用户在学习时记录自己的理解文本，与AI版本并列展示。含 `replaceAnswer` 开关，开启后可替代卡片原始答案 |
| **思维中间层** | 课本省略的逻辑跳跃 B（A→C 中缺失的 B），由 AI 自动补全 |
| **判断链** | 从原理推导出结论的完整推理步骤，非单纯结论 |
| **理解4层次** | 联系→解释→迁移→生成，知识深化的四个阶段 |
| **四大机制** | 思维补全、演绎链、抽象塔、边界地图 |
| **两阶段扫描** | 第一遍识别全部知识点，第二遍逐卡生成（解决悬空链接） |
| **中间产物** | 第一遍扫描产出的知识点标题清单，持久化供增量更新 |
| **转录本处理器** | 预处理子 Skill，将录音文字版/笔记清洗重组为结构化文本 |
| **答案** | 考试默写内容，学生需要直接背诵并在答题时输出的内容。来源可为用户指定、AI 从资料提取或 AI 自动生成 |
| **记忆技巧** | AI 从卡片内容自动生成的三类记忆辅助：关键词（纯术语列表）、记忆辅助（口诀/类比/意象/解释）、层级关系图（Mermaid flowchart）、对比表格（Markdown 表格）。关键词支持用户在学习视图中直接编辑修改 |
| **知识接口** | 知识点之间的关联链接，位于卡片末尾，标注关系性质（如"我是 X 的前提"）。链接可点击跳转到对应卡片 |
| **学习应用** | 由 learning-app Agent 从卡包 JSON 生成的交互式 HTML 应用，含折叠面板、拖拽排序、概念重组等功能 |

## 架构决策

- **文件解析**：复用已有的 `pdf` skill，不另写 `parser.py`
- **非教材材料预处理**：新增 `transcript-processor` 子 Skill，处理录音文字版和笔记的清洗、主题拆分、跨文档整合
- **模块化设计**：1 个主 Skill + 若干子 Skill（作为功能函数被主 Skill 编排调用）
  - **转录本预处理**（子 Skill）：录音稿/笔记 → 结构化 Markdown
  - **知识点提取**（子 Skill）：纯文本 + 可选大纲 → 知识标题清单
  - **类型诊断**（子 Skill）：知识点标题 + 对应内容 → 内容类型（A/B/C/D/mixed）
  - **卡片生成**（子 Skill）：知识点标题 + 对应内容 + 类型诊断 → 一张完整卡片（含理解路径 + 记忆技巧）
- **内容类型颜色编码**：A（逻辑序列）蓝色、B（机制/机理）紫色、C（结构/模型）绿色、D（概念辨析）橙色、mixed 用对应颜色的渐变/分割（各占一半），应用于卡片背景
- **记忆技巧字段**：`keywords`（纯术语列表）、`memory_aids`（口诀/类比/意象/解释）、`hierarchy`（层级图）、`comparison_tables`（对比表）
- **Python 脚本形态**：封装为 MCP 工具，供 AI 自动调用（非手动运行）
- **持久化**：`knowledge_store` 作为 MCP 工具，管理知识点清单和版本
- **格式输出**：`card_generator` 作为 MCP 工具，输出 Markdown + JSON，同时校验卡片字段完整性
- **增量更新**：保存中间产物知识点清单，版本号递增
- **HTML 应用模板化**：learning-app Agent 使用 templates/ 目录中的 HTML/CSS/JS 模板，每次只注入 data.json，避免重复造轮子
- **纯前端**：HTML 应用零框架零依赖，双击 index.html 即可运行，数据存 localStorage

## 文件结构

```
c:\Users\12977\Desktop\jiyikapian\
├── .agents\skills\
│   ├── understanding-memory\SKILL.md    # 主 Skill：编排整个流程
│   ├── learning-app\                    # ★ 新增：交互式学习应用
│   │   ├── SKILL.md                     # Agent prompt
│   │   ├── templates\                   # HTML 模板
│   │   │   ├── index.html
│   │   │   ├── style.css
│   │   │   └── app.js
│   │   └── scripts\
│   │       └── generate_app.py          # 生成脚本：JSON → HTML 应用
│   ├── transcript-processor\SKILL.md    # 子 Skill：预处理录音稿/笔记（v3 新增）
│   ├── knowledge-extractor\SKILL.md     # 子 Skill：提取知识点
│   ├── card-generator\SKILL.md          # 子 Skill：生成单张卡片
│   └── memory-techniques\SKILL.md       # 子 Skill：生成记忆技巧
├── scripts\
│   ├── __init__.py
│   ├── models.py                        # 数据模型：KnowledgeCard / MemoryTechniques / CardPack（含 to_dict/from_dict 序列化方法）
│   ├── knowledge_store.py               # MCP 工具：持久化读写 + 版本管理
│   ├── card_generator.py                # 输出格式化：generate_markdown() / generate_json() / generate_knowledge_graph()
│   ├── validator.py                     # 卡包数据校验器：validate_card_pack() + ValidationError 异常
│   ├── requirements.txt                 # 依赖
│   └── setup.ps1                        # 初始化脚本
├── docs\
│   ├── spec\2026-06-02-understanding-memory-skill-design.md
│   ├── spec\2026-06-03-card-structure-redesign.md
│   ├── spec\2026-06-03-v3-flashcard-design.md     # v3 设计文档：背诵模式+记忆曲线+概念填空+三视图
│   ├── README.md                        # 使用说明
│   ├── implementation-plan.md           # v1 实施计划
│   └── implementation-plan-v2.md        # v2 实施计划
├── output\
│   ├── processed\                       # 预处理中间产物（_已处理.md / _已整合.md）
│   └── card-app\                        # 学习应用输出（自动生成）
├── CONTEXT.md
└── 原始讨论\v1.txt
```


## 第一阶段范围

仅卡包生成。检测问答、判析反馈、HTML 导出为后续规划。

## 触发方式

用户上传文件（教材/课堂录音文字版/课堂笔记/考点大纲）后，说"帮我生成理解路径"或"生成卡包"即可触发。

## 知识点拆分规则

- **有考点大纲**：大纲中的每个条目 = 一张卡（大纲和教材分开上传）
- **无考点大纲**：一个独立的核心概念 = 一张卡
- **数量不做限制**