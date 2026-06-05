# 类型驱动升级 — 实施计划 (v3)

## 实施顺序

按依赖关系排列：下游依赖上游先完成。

```
Phase 1: 诊断 Skill（新建）       ← 无依赖
Phase 2: card-generator（升级）   ← 依赖诊断 Skill 的输入格式
Phase 3: memory-techniques（升级）← 依赖 card-generator 的 JSON 格式
Phase 4: understanding-memory（编排器升级）← 依赖前三者
Phase 5: learning-app（前端升级） ← 依赖卡包 JSON 新字段
```

---

## Phase 1：新建诊断 Skill

**文件**：`.agents/skills/type-diagnoser/SKILL.md`

**任务**：
1. 创建 type-diagnoser 目录和 SKILL.md
2. Prompt 包含：四类特征描述 + 判断规则 + 输出格式要求

**输出格式**：
```json
{
  "content_type": "A|B|C|D|mixed",
  "rationale": "...",
  "subtype_hints": { "has_sequence": bool, "has_causality": bool, "has_comparison": bool, "has_hierarchy": bool }
}
```

---

## Phase 2：升级 card-generator

**文件**：`.agents/skills/card-generator/SKILL.md`

**改动**：
1. 输入新增 `content_type` + `subtype_hints` 参数说明
2. Prompt 开头新增类型分支指令（§2.1 策略表）
3. decomposition 生成指令按类型调整（§2.2）
4. scenario_question + judgment_chain 按类型调整（§2.3）
5. 新增三层覆盖检查指令（§2.4），生成后逐层验证
6. 输出 JSON 中透传 `content_type` 字段

---

## Phase 3：升级 memory-techniques

**文件**：`.agents/skills/memory-techniques/SKILL.md`

**改动**：
1. 输入新增读取卡片 JSON 中的 `content_type` 字段
2. keywords 输出格式改为纯词列表
3. 新增 `memory_aids` 字段（替换原 `keyword_explanations`）
4. 技巧生成规则按类型调整（§3.2 策略表）
5. 四类专属技巧的生成指令 + 输出格式（§3.3）
6. 删除旧的树形结构关键词格式

---

## Phase 4：升级 understanding-memory 编排器

**文件**：`.agents/skills/understanding-memory/SKILL.md`

**改动**：
1. 第4步子流程从 3 步改为 5 步
2. 新增类型诊断步骤调用
3. 新增用户确认诊断结果的交互指令
4. card-generator 调用参数增加诊断结果
5. 错误处理新增诊断相关分支

---

## Phase 5：升级 learning-app 前端

**文件**：
- `.agents/skills/learning-app/templates/style.css`
- `.agents/skills/learning-app/templates/card-view.js`
- `.agents/skills/learning-app/templates/index.html`（可能）
- `.agents/skills/learning-app/scripts/generate_app.py`（可能）

**改动**：
1. 定义四类颜色 CSS 变量 + mixed 渐变
2. 卡片渲染时根据 `content_type` 应用背景色
3. `keywords` 渲染从树形缩进改为列表展示
4. 在卡片上展示内容类型标签（可选，辅以颜色）

---

## 工作量估算

| Phase | 文件数 | 改动类型 | 预估 |
|:---|:---:|:---|:---:|
| 1. 诊断 Skill | 1 新建 | 全新建 | ~40行 |
| 2. card-generator | 1 修改 | 大改 | ~80行 |
| 3. memory-techniques | 1 修改 | 中改 | ~60行 |
| 4. understanding-memory | 1 修改 | 中改 | ~30行 |
| 5. learning-app | 2-3 修改 | 中改 | ~50行 |