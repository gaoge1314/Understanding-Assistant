---
name: learning-app
description: 从卡包 JSON 生成交互式 HTML 学习应用，并在用户学习时提供 AI 辅导
description_for_model: 生成交互式 HTML 学习应用。读取 output/json/ 中的卡包 JSON，拷贝模板，注入数据，输出可直接双击打开的 HTML 应用
trigger: 用户说"生成学习应用 / 打开交互式卡包 / 帮我生成HTML版本 / 打开学习应用"等
---

# learning-app

## 触发时机

用户说以下任一表述时触发：
- "生成学习应用"
- "打开交互式卡包"
- "帮我生成 HTML 版本"
- "打开学习应用"
- 其他等价表述

## 处理流程

### Step 1：检查卡包数据

检查 `output/json/` 目录下是否存在卡包 JSON 文件（*.json）。

- 如果有：选择最新版本，进入 Step 2
- 如果没有：引导用户先使用 understanding-memory 生成卡包

```
output/json/
├── 灾害学_v1.json
├── 灾害学_v2.json          ← 自动选最新版本
└── ...
```

### Step 2：执行生成脚本

运行脚本：
```powershell
cd .agents\skills\learning-app
python scripts\generate_app.py <卡包JSON路径>
```

脚本自动完成：
1. 读取 JSON 卡包数据
2. 对每张卡片执行：
   - 判断 `reconstruct_type` 数组（详见下方规则）
   - 生成 `blanks` 填空数据
3. 拷贝 templates/ 中的 index.html、style.css、app.js
4. 注入数据到 data.json
5. 输出到 `output/card-app/{科目名}/`

#### reconstruct_type 判断规则

```python
# 返回数组，可包含多个值
reconstruct_type = ["reorder", "fill-blank"]

# "reorder" — 平行概念拖拽排序
#   条件：decomposition 条目数 ≥ 2，且为平行关系
#         （非因果链，或标题含"要素/类型/分类/阶段"等词）

# "fill-blank" — 概念填空
#   条件：answer 字段长度 ≥ 20 字，且有可挖关键词
#   脚本自动从 answer/decomposition/keywords 中提取术语生成 blanks
```

### Step 3：通知用户

输出完成后，告知用户：
> ✅ 学习应用已生成！
> 打开以下文件即可开始学习：
> `output/card-app/{科目名}/index.html`
>
> 功能包括：
> • **折叠面板** — 按需展开卡牌四段内容
> • **拖拽排序** — 调整左侧目录顺序、创建分组
> • **概念重组** — 将打乱的概念块拖到正确位置
> • **概念填空** — 填写关键术语巩固理解（右侧栏下拉切换）
> • **用户笔记** — 记录自己的理解，与AI版本对比
> • **三视图导航** — 学习/背诵/复习顶部Tab切换
> • **每日字数设置** — 200/500/1000/3000 字，自动推荐卡片
> • **翻转背诵 + 记忆曲线** — 正面看题、翻转看答案、记得/忘了反馈
> • **复习视图** — 查看各卡片复习进度和记忆曲线状态

### Step 4：AI 辅导模式

用户打开 HTML 应用学习后，回到 Trae 对话时：

1. 主动询问用户当前在学习什么（可参考背诵视图的进度）
2. 根据用户回答的卡片名称，提供：
   - **苏格拉底式追问**：针对卡片核心概念提问
   - **类比辅助**：用生活场景类比
   - **知识连接**：将当前卡片与其他卡片关联
3. 如果用户说"帮我出题"，基于卡片内容生成检测题
4. 如果用户说"安排复习"，提示用户在背诵视图中设置每日字数

## 文件结构

```
.agents/skills/learning-app/
├── SKILL.md                     ← 本文件（Agent prompt）
├── templates/                   ← HTML 模板（无需修改）
│   ├── index.html               ← 三视图 + 模态框 + 填空
│   ├── style.css                ← 翻转卡 + Tab + 复习视图样式
│   └── app.js                   ← v3: 三视图/记忆曲线/填空/笔记
└── scripts/
    └── generate_app.py          ← 生成脚本（v3: 数组型 reconstruct_type + blanks）
```