# 知识关联图谱设计文档

## 概述

为卡片学习应用增加"知识关联"能力，让孤立的知识点通过关系网络连接起来，实现**分组背诵**和**网状理解**。

## 总体架构

```
┌─────────────────────────────────────────┐
│           构建工具链（Python）              │
│                                           │
│  原始数据（文档 / JSON）                   │
│       ↓                                   │
│  LightRAG (LLM 抽取实体 + 关系)            │
│       ↓                                   │
│  适配脚本 (scripts/build_relations.py)     │
│       ↓                                   │
│  增强的 card JSON (含 relations 字段)       │
└──────────────────────┬──────────────────┘
                       │ (一次性输出)
┌──────────────────────▼──────────────────┐
│       前端学习应用（纯静态 HTML/JS）        │
│                                           │
│  卡片视图新增 "⑤ 关联" 折叠面板              │
│    - 径向布局：当前卡片居中，关联环绕          │
│    - SVG 连线和关系标签                     │
│    - 点击跳转关联卡片                       │
│  用户自定义关联（存 localStorage）           │
│  保留所有现有功能不变                       │
└─────────────────────────────────────────┘
```

**关键原则**：LightRAG 只在构建时运行一次，输出固化到 JSON，前端保持零运行时依赖。

---

## 一、数据层：relations 字段

### 1.1 数据结构

每张卡片新增 `relations` 数组，替换现有 `knowledge_interfaces`：

```js
{
  "title": "灾害链",
  // ... 原有字段不变
  "relations": [
    {
      "targetId": "na-tech事件",
      "type": "expand",
      "label": "自然灾害引发技术事故是灾害链的特例"
    },
    {
      "targetId": "应对灾害链的策略",
      "type": "expand",
      "label": "断链、削弱、转移、避让、接受"
    },
    {
      "targetId": "多米诺效应",
      "type": "contrast",
      "label": "都是连锁反应，但触发场景和机制不同"
    }
  ]
}
```

### 1.2 关系类型

| 类型 | 标签 | 语义 | 配色 |
|------|------|------|------|
| `expand` | 展开 | A 是 B 的具体化/展开 | 蓝色 `#3b82f6` |
| `generalize` | 概括 | A 是 B 的概括/抽象 | 紫色 `#8b5cf6` |
| `contrast` | 对比 | A 与 B 对比辨析 | 橙色 `#f59e0b` |
| `theorize` | 理论 | A 是 B 的理论基础 | 绿色 `#10b981` |
| `apply` | 实践 | A 是 B 的实践应用 | 青色 `#06b6d4` |
| `precede` | 前置 | A 在 B 之前 | 灰色 `#6b7280` |
| `succeed` | 后继 | A 在 B 之后 | 黄色 `#eab308` |

### 1.3 数据迁移

现有 JSON 中的 `knowledge_interfaces` 全部自动转为 `expand` 类型：

```js
// 迁移前
"knowledge_interfaces": [
  {"target_card_id": "Na-tech事件", "target_title": "Na-tech事件", "relation": "..."}
]

// 迁移后
"relations": [
  {"targetId": "Na-tech事件", "type": "expand", "label": "..."}
]
```

---

## 二、LightRAG 构建工具链

### 2.1 安装

从本地源码安装 LightRAG：

```bash
cd LightRAG-main
pip install -e .
```

### 2.2 配置

使用 DeepSeek API：

```python
rag = LightRAG(
    working_dir="./rag_storage",
    llm_model_func=deepseek_complete,
    embedding_func=deepseek_embed,
)
```

### 2.3 工作流程

```
输入：原始文档（.txt）或现有卡包 JSON 中的答案文本
  ↓
1. LightRAG 文档分块
2. LLM 抽取实体和关系
3. 输出知识图谱 (graphml)
  ↓
适配脚本 (scripts/build_relations.py)：
  - 读取 graphml 中的边（关系）
  - 匹配边两端的实体名到卡片 ID
  - 根据关系描述自动归类（expand/contrast/generalize 等）
  - 输出 relations 数据
  ↓
写入增强的 JSON 文件
```

### 2.4 适配脚本核心逻辑

```python
def graphml_to_relations(graphml_path, card_titles):
    """将 LightRAG 输出的 graphml 转为卡片 relations"""
    G = nx.read_graphml(graphml_path)
    relations = {title: [] for title in card_titles}

    for u, v, data in G.edges(data=True):
        if u in card_titles and v in card_titles:
            desc = data.get("description", "")
            rel_type = classify_relation(desc)
            relations[u].append({
                "targetId": v,
                "type": rel_type,
                "label": desc
            })
            # 双向关系
            relations[v].append({
                "targetId": u,
                "type": rel_type,
                "label": desc
            })
    return relations
```

---

## 三、前端 UI — "⑤ 关联" 面板

### 3.1 位置

卡片视图从 4 个折叠面板变为 5 个：

| 序号 | 板块 | 来源 |
|------|------|------|
| ① | 答案（考试默写） | 不变 |
| ② | 理解路径 | 不变 |
| ③ | 记忆技巧 | 不变 |
| ~~④~~ | ~~与其他知识的关键接口~~ | **删除** |
| ⑤ | 关联 | **新增** |

### 3.2 径向布局

```
┌──────────────────────────────────────┐
│ ▼ ⑤ 关联 (3)                         │
│                                      │
│           [关联卡片 A]                │
│           展开                        │
│         ╱                            │
│   [当前卡片] ─── [关联卡片 B]          │
│   灾害链      对比                    │
│         ╲                            │
│           [关联卡片 C]                │
│           展开                        │
│                                      │
│   [+ 添加关联]                        │
└──────────────────────────────────────┘
```

### 3.3 HTML 结构

```html
<details class="card-section" open>
  <summary>⑤ 关联 <span class="rel-count">(3)</span></summary>
  <div class="relation-graph">
    <svg class="relation-lines">
      <!-- 由 JS 动态绘制连线和文字标签 -->
    </svg>
    <div class="relation-nodes">
      <div class="rel-node current" data-card-index="3">
        <span class="rel-title">灾害链</span>
      </div>
      <div class="rel-node" data-card-index="4">
        <span class="rel-type expand">展开</span>
        <span class="rel-title">Na-tech事件</span>
      </div>
      <div class="rel-node" data-card-index="6">
        <span class="rel-type contrast">对比</span>
        <span class="rel-title">多米诺效应</span>
      </div>
    </div>
    <div class="rel-footer">
      <button class="btn-add-relation">+ 添加关联</button>
    </div>
  </div>
</details>
```

### 3.4 交互行为

| 操作 | 行为 |
|------|------|
| 点击关联卡片 | 跳转到目标卡片（保留现有知识链接跳转逻辑） |
| 悬停关联卡片 | 高亮对应的连线和文字标签 |
| 悬停连线标签 | 高亮两端节点 |
| + 添加关联 | 弹出模态框：搜索卡片 → 选关系类型 → 写描述 |

### 3.5 JS 布局计算

关联卡片的环绕位置基于当前卡片坐标计算：

```js
function calcPositions(centerX, centerY, count, radius) {
  const positions = [];
  for (let i = 0; i < count; i++) {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    positions.push({
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    });
  }
  return positions;
}
```

- 关联 ≤ 4 个：单圈均匀环绕
- 关联 5-6 个：两圈排列
- 关联 > 6 个：可滚动

### 3.6 SVG 连线

```js
function drawLines(svg, center, positions, labels) {
  positions.forEach((pos, i) => {
    // 连线
    svg.append('line', {
      x1: center.x, y1: center.y,
      x2: pos.x, y2: pos.y,
      class: 'rel-line'
    });
    // 关系标签（连线中点偏移）
    const mx = (center.x + pos.x) / 2;
    const my = (center.y + pos.y) / 2;
    svg.append('text', {
      x: mx, y: my,
      class: 'rel-label'
    }).text(labels[i]);
  });
}
```

---

## 四、用户自定义关联

### 4.1 state.js 扩展

在 `cardStates` 中新增 `customRelations`：

```js
// 每个卡片的 state
{
  expanded: { answer: true, path: true, memory: true, interface: true },
  // ... 已有字段不变
  customRelations: []  // 新增：用户自定义的关系
}
```

### 4.2 渲染合并逻辑

```js
function getRelations(card) {
  const preset = card.relations || [];
  const custom = AppState.getCardState(card.title).customRelations || [];
  return [...preset, ...custom];
}
```

### 4.3 添加关联模态框

点击 "+ 添加关联" 后弹出：

```
┌─ 添加关联 ─────────────────────┐
│                                 │
│  搜索目标卡片: [___________]     │
│                                 │
│  关系类型: [展开 ▼]              │
│                                 │
│  关系描述: [________________]    │
│                                 │
│         [取消]    [保存]         │
└─────────────────────────────────┘
```

---

## 五、修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/build_relations.py` | **新建** | LightRAG 适配脚本 |
| `output/json/灾害学_v5.json` | **修改** | `knowledge_interfaces` → `relations` |
| `output/card-app/灾害学/card-view.js` | **修改** | 替换第④ section 为第⑤ 径向图 |
| `output/card-app/灾害学/state.js` | **修改** | 新增 `customRelations` 默认值 |
| `output/card-app/灾害学/style.css` | **修改** | 新增径向布局/SVG/模态框样式 |
| `output/card-app/灾害学/index.html` | **不变** | 无结构性变化 |

---

## 六、不做的事（明确排除）

本设计不包含以下内容，留待后续迭代：

- **关联背诵模式**（串讲/对比提问）— 后续再实现
- **白板模式**（拖拽连线自定义关系）— 后续再实现
- **关系检测题**（选择题考关系）— 后续再实现
- 左右栏折叠按钮 — 后续再实现