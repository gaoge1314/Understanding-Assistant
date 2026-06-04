# 3. 卡片唯一标识 + 知识接口结构化引用

- **日期**：2026-06-03
- **状态**：已批准

## 背景

v4 升级中，知识接口需要从纯文本升级为可点击跳转链接。现有实现中，`knowledge_interfaces` 是 `List[str]`，存储自由文本如 `"→ 灾害系统动力学机制：系统各要素的动态关系"`，渲染时靠文本解析提取目标卡片标题。

## 决策

### 1. 为每张卡片分配唯一标识

在 `KnowledgeCard` 中新增 `card_id` 字段：

```python
@dataclass
class KnowledgeCard:
    card_id: str = ""  # 唯一标识，由标题自动生成
    # ... 其他字段
```

`card_id` 在卡包生成时自动填充：从标题提取拼音缩写或使用 UUID，确保在同一卡包内唯一。

### 2. 知识接口改为结构化引用

```python
@dataclass
class KnowledgeInterface:
    target_card_id: str   # 目标卡片唯一标识
    relation: str = ""    # 关系说明文本
```

### 3. 生成时解析引用

`generate_app.py` 在富化卡片数据时：
1. 为每张卡片生成 `card_id`
2. 解析原有 `knowledge_interfaces` 文本中的标题
3. 按精确标题匹配找到目标卡片的 `card_id`
4. 在输出 data.json 中同时保留原始文本和解析后的引用

### 4. data.json 输出格式

```json
{
  "cards": [
    {
      "card_id": "zhaihai-xitong",
      "title": "灾害系统",
      "knowledge_interfaces": [
        {
          "text": "→ 灾害系统动力学机制：系统各要素的动态关系",
          "target_card_id": "zhaihai-xitong-donglixue-jizhi",
          "relation": "系统各要素的动态关系"
        }
      ]
    }
  ]
}
```

### 5. 前端渲染

`app.js` 中 `formatInterfaces()` 遍历知识接口列表：
- 有 `target_card_id` → 渲染为 `<a class="knowledge-link" data-card-index="N">`（N 通过 `card_id` 查表获得）
- 无 `target_card_id`（匹配失败）→ 降级为纯文本
- `target_card_id` 指向自身 → 不生成链接

## 备选方案

- **文本解析方案**：不修改数据模型，仅在 `app.js` 中通过正则匹配标题。放弃，因为不稳定（标题包含特殊字符、重名等问题），且无法支持未来扩展（如卡片依赖图）。
- **仅用标题匹配**：用标题文本替代 `card_id`，在渲染时实时查找。放弃，因为标题可能重复或变更，链接稳定性差。

## 影响

- **正面**：引用稳定、可扩展（可演进为双向链接、知识图谱）、生成时一次性解析，运行时零开销
- **负面**：需要修改 `models.py`、`generate_app.py`、`app.js` 三个文件；现有卡包 JSON 需要重新生成才能获得结构化引用