# 路径二剩余功能实现方案

## 概述

完成中间概念层（路径二）的剩余工作：前端径向图关联面板、semantic_profile 完善、build_relations.py 重构与增强、generate_app.py 集成自动化。

## 背景

build_relations.py 已完成 5 步流水线（数据准备 → LLM 聚类 → 卡片绑定 → 关系推导 → 输出），但：
- 前端仍使用旧版「④ 知识接口」（knowledge_interfaces），未展示新版「⑤ 关联」（relations）
- semantic_profile.function_tag 和 semantic_profile.abstract 字段为空
- generate_app.py 未集成关系构建流程
- Python 数据模型（models.py）未定义 relations 和 semantic_profile 字段

## 1. 数据模型更新（models.py）

### 变更

KnowledgeCard 新增两个字段：

```python
@dataclass
class KnowledgeCard:
    # ... 现有字段不变
    knowledge_interfaces: List[KnowledgeInterface] = field(default_factory=list)  # 后向兼容
    relations: List[dict] = field(default_factory=list)         # ⑤ 关联（新）
    semantic_profile: dict = field(default_factory=dict)         # 语义画像（新）
```

- `to_dict()` 输出 relations + semantic_profile
- `from_dict()` 读取 relations + semantic_profile（若不存在则取默认值）
- 保持 knowledge_interfaces 后向兼容

## 2. build_relations.py 重构

### 2.1 模块化拆分

将现有 `main()` 拆分为两个入口：

```python
# 模块级 API（供 generate_app.py import）
async def build_relations(input_path, output_path, rag_dir, output_dir, force=False):
    """5 步流水线主函数"""
    ...

# CLI 入口（保持手动运行能力）
async def main():
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()
    await build_relations(args.input, args.output, args.rag_dir, args.output_dir, args.force)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.2 Step 4 增强：精修时顺带生成 function_tag + abstract

在 build_refine_prompt 中嵌入每张卡片的完整数据（title + core_principle + answer 摘要），让 LLM 在精修关系时一并输出每张卡片的：

- `function_tag` — 功能标签：`mechanism_description` / `comparison_analysis` / `process_flow` / `structural_model` / `practical_guideline`
- `abstract` — 一句话抽象概括（≤50 字）

Prompt 输出格式扩展：

```json
{
  "refined_relations": [...],
  "card_profiles": [
    {
      "title": "灾害链",
      "function_tag": "mechanism_description",
      "abstract": "描述一种灾害引发一系列灾害的连锁现象"
    }
  ]
}
```

Step 5 写入卡片时填充 `semantic_profile.function_tag` 和 `semantic_profile.abstract`。

## 3. 前端模板更新

### 3.1 card-view.js 模板

**替换 section 配置**（renderCardContent 中）：

```
{ id: 'interface', label: '④ 与其他知识的关键接口', content: formatInterfaces(card) }
→
{ id: 'relation', label: '⑤ 关联', content: formatRelations(card) }
```

**新增 formatRelations(card) 函数**：

```
1. 读取 card.relations[]，若为空则返回 ''
2. 按 targetId（卡片标题）匹配到 APP.cardData 中的索引
3. 构建径向布局容器：
   <div class="relation-graph">
     <svg class="relation-svg">（动态绘制连线 + 关系标签）</svg>
     <div class="relation-nodes">
       <div class="relation-node current">当前卡片</div>
       <div class="relation-node" data-index="N">关联卡片</div>
     </div>
   </div>
4. 环绕位置计算：angle = 2π*i/N - π/2，半径固定 90px
5. SVG 连线：从中心 (120,120) 到每个节点位置，stroke 颜色按关系类型
6. SVG 标签：连线中点偏移显示关系类型中文名
7. 悬停高亮：连线 stroke-width: 2→3 + 节点背景高亮联动
```

**事件委托更新**：
- 点击 `.relation-node`（非 current）→ selectCard(index)
- 保留原有 `.knowledge-link` 点击处理（后向兼容）

### 3.2 state.js 模板

默认 expanded 状态添加 `relation: true`：

```javascript
expanded: { answer: true, path: true, memory: true, interface: true, relation: true }
```

v2→v3 迁移代码同步更新。

### 3.3 style.css 模板

新增样式：

| 选择器 | 用途 |
|:---|:---|
| `.relation-graph` | 容器，相对定位，min-height: 260px |
| `.relation-svg` | 绝对定位覆盖容器 |
| `.relation-node` | 卡片节点，圆角矩形 padding: 8px 14px |
| `.relation-node.current` | 当前卡片居中，font-weight: 600 |
| `.relation-node:hover` | 背景高亮 + cursor: pointer |
| `.relation-line` | SVG line, stroke-width: 2 |
| `.relation-line:hover` | stroke-width: 3 |
| `.relation-label` | SVG text, font-size: 11px, fill: #6b7280 |
| `.rel-line.expand` | stroke: #3b82f6 |
| `.rel-line.contrast` | stroke: #f59e0b |
| `.rel-line.generalize` | stroke: #8b5cf6 |
| `.rel-line.theorize` | stroke: #10b981 |
| `.rel-line.apply` | stroke: #06b6d4 |
| `.rel-line.precede` | stroke: #6b7280 |
| `.rel-line.succeed` | stroke: #eab308 |

### 3.4 关系类型配色

| 类型 | 中文标签 | 颜色 |
|:---|:---|:---|
| expand | 展开 | #3b82f6 (蓝) |
| contrast | 对比 | #f59e0b (橙) |
| generalize | 概括 | #8b5cf6 (紫) |
| theorize | 理论 | #10b981 (绿) |
| apply | 实践 | #06b6d4 (青) |
| precede | 前置 | #6b7280 (灰) |
| succeed | 后继 | #eab308 (黄) |

## 4. generate_app.py 集成

### 4.1 异步改造

main() 改为 async，在开头调用 build_relations()：

```python
async def main():
    # Step 1: 构建关系（如需要）
    if args.build_relations:
        from scripts.build_relations import build_relations
        await build_relations(args.input, args.output, rag_dir, output_dir, force=args.force)
    
    # Step 2: 生成应用（现有逻辑）
    generate_app(args.output if args.build_relations else args.input, args.output_dir)

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.2 CLI 参数扩展

新增参数 `--build-relations`、`--rag-dir`、`--force`：

```bash
python generate_app.py output/json/灾害学_v5.json --build-relations --rag-dir rag_storage
```

## 5. 执行顺序

```
1. ✅ models.py 更新（已完成）
2. build_relations.py 重构（模块 API + Step 4 增强）
3. card-view.js 模板更新（formatRelations）
4. state.js 模板更新（expanded 默认值）
5. style.css 模板更新（径向图样式）
6. generate_app.py 集成（异步 + import）
7. 运行 build_relations.py → 生成 v13 JSON（含 function_tag + abstract）
8. 运行 generate_app.py → 重新生成 card-app
```

## 已排除范围

- 不改动现有背诵/复习/计划视图
- 不改动右侧栏（概念重组、概念填空）
- 不引入新依赖
- 不修改 LightRAG
- 不加用户自定义关联功能（后续迭代）