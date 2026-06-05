---
title: "ADR-0005: 修复 state.js 对象字面量语法错误"
status: "Accepted"
date: "2026-06-04"
authors: ["诊断 Agent"]
tags: ["architecture", "bug-fix", "javascript"]
supersedes: ""
superseded_by: ""
---

# ADR-0005: 修复 state.js 对象字面量语法错误

## Status

**Accepted**

## Context

在"灾害学"卡包的运行中，浏览器控制台报出两条错误：

1. `SyntaxError: Unexpected token ';'`（来自 `state.js`）
2. `ReferenceError: AppState is not defined`（来自 `app.js:175`）

经定位，`state.js` 第 102-119 行的 `getCardState()` 函数中存在对象字面量结构错误：
`myUnderstanding` 和 `myCreation` 两个属性被错误地嵌套在 `customVersions` 对象内部，导致外层对象（`s.cardStates[title] = { ... }`）缺少闭合的 `}` 符号。JavaScript 解析器在第 116 行遇到多余的 `};` 时抛出 `SyntaxError: Unexpected token ';'`。

由于 `state.js` 的 IIFE 因语法错误完全无法执行，`window.AppState` 全局对象从未被定义。后续 `app.js` 中第 175 行调用 `AppState.loadState()` 时自然抛出 `ReferenceError: AppState is not defined`。

该问题存在于通过 `generate_app.py` 生成的模板代码中，影响所有通过该生成器创建的卡包应用。

## Decision

将 `myUnderstanding` 和 `myCreation` 两个属性从 `customVersions` 对象内部提升到外层对象的顶层，确保对象字面量结构正确闭合。

**修改前（错误结构）：**

```javascript
s.cardStates[title] = {
    expanded: { ... },
    customVersions: { myUnderstanding: '',    // ← 错误嵌套
        myCreation: '',                       // ← 错误嵌套
        customVersions: { ... },              // ← 嵌套的 customVersions
        editedKeywords: null,
        isCompleted: false
    };                                        // ← 此处 }; 缺少外层闭合 }
```

**修改后（正确结构）：**

```javascript
s.cardStates[title] = {
    expanded: { ... },
    myUnderstanding: '',      // ← 提升到顶层
    myCreation: '',           // ← 提升到顶层
    customVersions: { ... },  // ← 独立的对象
    editedKeywords: null,
    isCompleted: false
};                            // ← 正确闭合外层对象
```

## Consequences

### Positive

- **POS-001**: `state.js` 语法检查通过，应用可正常加载
- **POS-002**: `AppState` 全局对象正确注册，`app.js` 中所有调用正常工作
- **POS-003**: `myUnderstanding` 和 `myCreation` 位于正确的对象层级，与其它模块（`card-view.js`）的使用方式一致

### Negative

- **NEG-001**: 该修复仅针对症状而非生成器根源——`generate_app.py` 模板中仍可能存在相同结构错误，需要同步修正生成器脚本
- **NEG-002**: 已生成的其它卡包如果使用了相同模板，同样存在此问题，需要逐一修复

## Alternatives Considered

### 保持嵌套 + 添加额外闭合

- **ALT-001**: **Description**: 在 `customVersions` 对象内保持 `myUnderstanding` 和 `myCreation` 不变，在 `};` 之前加一个 `}` 闭合外层对象
- **ALT-002**: **Rejection Reason**: 这样会产生双层 `customVersions` 嵌套（外层 customVersions 包含内层 customVersions），数据结构混乱，且与其他模块读取 `state.myUnderstanding` 的逻辑不符

### 移除未使用的属性

- **ALT-003**: **Description**: 直接删除 `myUnderstanding` 和 `myCreation` 属性
- **ALT-004**: **Rejection Reason**: 其他模块（如 `card-view.js`）确实会读取 `state.myUnderstanding` 和 `state.myCreation`，删除会导致运行时错误

## Implementation Notes

- **IMP-001**: 修复已应用到 `output/card-app/灾害学/state.js`，通过 `node --check` 验证语法正确
- **IMP-002**: 所有 8 个 JS 文件均通过语法检查，无其他语法错误
- **IMP-003**: **后续必须同步修复** `generate_app.py` 中的模板字符串，防止新生成的卡包再次出现相同问题
- **IMP-004**: 建议对其他已生成的卡包目录执行 `node --check *.js` 批量验证

## References

- **REF-001**: [ADR-0003: 卡片唯一标识](file:///c:/Users/12977/Desktop/jiyikapian/docs/adr/0003-card-unique-identifier.md)
- **REF-002**: [ADR-0004: Path2 剩余功能实现](file:///c:/Users/12977/Desktop/jiyikapian/docs/adr/0004-path2-remaining-implementation.md)
- **REF-003**: [state.js 修复后代码](file:///c:/Users/12977/Desktop/jiyikapian/output/card-app/灾害学/state.js)