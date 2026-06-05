---
title: "ADR-0006: 侧栏折叠/展开功能实现方案"
status: "Accepted"
date: "2026-06-05"
authors: "User + AI Assistant"
tags: ["architecture", "ui", "persistence"]
supersedes: ""
superseded_by: ""
---

# ADR-0006: 侧栏折叠/展开功能实现方案

## Status

**Accepted**

## Context

学习应用卡包采用三栏 flex 布局（左侧栏 sidebar 220px + 主内容区 content flex:1 + 右侧栏 rightbar 260px）。用户在学习时需要临时收起侧栏以获得更大的内容阅读区域，或在需要时重新展开。需求包括：

1. 左右侧栏可独立折叠/展开
2. 两种触发方式：点击头部区域 或 点击边缘按钮
3. 折叠后保留窄条（~32px），窄条上显示展开箭头按钮
4. 折叠状态需持久化，刷新后恢复

## Decision

采用 **CSS Transition + 最小化 JS IIFE 模块** 方案，具体决策点如下：

- **DEC-001**: 使用 CSS 类 `.collapsed` 控制折叠状态，通过 `transition: width 0.25s ease` 实现平滑动画
- **DEC-002**: 折叠状态归入 `AppState.state` 统一持久化，而非创建独立的 localStorage key
- **DEC-003**: 新建 IIFE 模块命名 `Collapser`，遵循 `Sidebar` / `Reorder` / `FillBlank` 风格
- **DEC-004**: 边缘按钮在折叠时铺满窄条（`position: static; width: 100%; height: 100%`），展开时贴在侧栏边缘（`position: absolute; right: 0`，不超出边界）
- **DEC-005**: 右侧栏头部点击排除 `<select>` 元素，防止切换模式时误触发折叠
- **DEC-006**: 折叠窄条仅显示箭头按钮（`▶`/`◀`），不加额外图标标识

## Consequences

### Positive

- **POS-001**: 改动范围小——新增约 70 行 CSS + 80 行 JS，不修改现有交互逻辑
- **POS-002**: 与现有 IIFE + window 暴露模式完全一致，无需重构
- **POS-003**: 状态与 `AppState` 统一存储，无多 key 同步风险
- **POS-004**: 动画平滑，用户体验良好

### Negative

- **NEG-001**: 折叠窄条（32px）空间有限，仅能容纳纯按钮，无法显示侧栏标识
- **NEG-002**: 依赖 `AppState.state` 加载完成后初始化，需注意 `Collapser` 加载顺序
- **NEG-003**: `generate_app.py` 模板需同步更新，否则新生成的卡包不包含此功能

## Alternatives Considered

### 独立 localStorage key

- **ALT-001**: **Description**: 使用独立的 `__CARD_PANEL_STATE__` localStorage key 持久化折叠状态
- **ALT-002**: **Rejection Reason**: 与现有 `AppState.saveState()` / `loadState()` 模式不一致，多 key 分散增加维护成本，折叠状态本质上属于应用状态

### 完全隐藏（width: 0）

- **ALT-003**: **Description**: 折叠后侧栏完全消失，主内容区占满全部空间
- **ALT-004**: **Rejection Reason**: 用户已选择保留窄条（32px），窄条上可见展开按钮，无需大幅移动鼠标去触发

### CSS Grid 重构

- **ALT-005**: **Description**: 将 main-layout 从 flex 重构为 `display: grid; grid-template-columns: auto 1fr auto`
- **ALT-006**: **Rejection Reason**: 改动范围过大，现有 flex 布局工作正常，grid 无实质收益

## Implementation Notes

- **IMP-001**: `Collapser` 模块加载顺序在 `state.js` 之后、`sidebar.js` 之前；初始化使用 `DOMContentLoaded` 事件，此时 `AppState.state` 已由 `app.js` 加载完毕
- **IMP-002**: `AppState.DEFAULT_STATE` 需新增 `sidebarCollapsed: false` 和 `rightbarCollapsed: false` 默认值
- **IMP-003**: `generate_app.py` 模板必须同步更新（CSS 模板 + HTML 模板 + 加载顺序），新生成的卡包才能包含此功能
- **IMP-004**: 边缘按钮的 z-index 设为 10，确保半叠在边框上时不被其他元素遮挡
- **IMP-005**: `isCompleted` 在 CONTEXT.md 中记录为"卡片学习完成状态"，与折叠功能无关，无须改动

## References

- **REF-001**: [ADR-0005: state.js 对象字面量语法修复](file:///c:/Users/12977/Desktop/jiyikapian/docs/adr/0005-state-js-object-literal-syntax-fix.md)
- **REF-002**: [Collapsible Panels Spec](file:///c:/Users/12977/Desktop/jiyikapian/docs/spec/2026-06-05-collapsible-panels-design.md)
- **REF-003**: [CONTEXT.md](/file:///c:/Users/12977/Desktop/jiyikapian/CONTEXT.md) — 术语「面板折叠」