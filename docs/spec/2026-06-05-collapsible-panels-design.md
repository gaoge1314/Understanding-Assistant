# 侧栏折叠/展开功能设计

## 概述

为学习应用卡包的左侧栏（目录）和右侧栏（学习模式）添加可折叠/展开功能，让用户在学习时能根据需求灵活控制侧栏的显示与隐藏，获得更大的主内容区空间。

## 背景

当前页面采用三栏 flex 布局：
- **左侧栏（sidebar）**：220px 宽，显示目录和卡片列表
- **主内容区（content）**：flex: 1，显示卡片内容
- **右侧栏（rightbar）**：260px 宽，显示学习模式（概念重组/概念填空）和 AI 辅导入口

用户在学习时可能需要临时收起侧栏以获得更大的内容阅读区域，或在需要时重新展开。

## 需求

1. 左侧栏（`aside.sidebar`）可独立折叠/展开
2. 右侧栏（`aside.rightbar`）可独立折叠/展开
3. 两种触发方式：点击头部区域 或 点击边缘折叠按钮
4. 折叠后保留窄条（~32px），窄条上显示展开按钮
5. 折叠状态持久化保存，刷新页面后恢复

## 方案选择

**推荐方案：CSS Transition + 最小化 JS 修改**

- 新增 CSS 类 `.collapsed`，通过 `transition: width 0.25s ease` 实现平滑动画
- 创建独立模块 `collapse.js`（IIFE + window 暴露模式），处理交互和持久化
- 使用 `localStorage` 持久化折叠状态

## 架构

### 样式变更（style.css 新增 v6 区块）

```css
.sidebar { transition: width 0.25s ease, min-width 0.25s ease; position: relative; }
.sidebar.collapsed { width: 32px; min-width: 32px; }
.sidebar.collapsed .sidebar-header,
.sidebar.collapsed .sidebar-groups,
.sidebar.collapsed .sidebar-footer { display: none; }

.rightbar { transition: width 0.25s ease, min-width 0.25s ease; position: relative; }
.rightbar.collapsed { width: 32px; min-width: 32px; }
.rightbar.collapsed .rightbar-mode,
.rightbar.collapsed .reorder-area,
.rightbar.collapsed .fill-area,
.rightbar.collapsed .ai-help { display: none; }

/* 边缘折叠按钮 */
.sidebar .collapse-btn, .rightbar .collapse-btn {
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 18px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid #e5e7eb; background: #fff; color: #9ca3af;
  font-size: 10px; cursor: pointer; z-index: 10; border-radius: 4px;
  transition: 0.15s;
}
.sidebar .collapse-btn { right: -9px; }
.rightbar .collapse-btn { left: -9px; }
.sidebar .collapse-btn:hover, .rightbar .collapse-btn:hover {
  background: #f3f4f6; color: #3b82f6;
}
.sidebar.collapsed .collapse-btn, .rightbar.collapsed .collapse-btn {
  position: static; margin: auto; transform: none;
  width: 100%; border: none; border-radius: 0; height: 100%;
}

.sidebar-header, .rightbar-mode { cursor: pointer; user-select: none; }
.sidebar-header:hover, .rightbar-mode:hover { background: #f3f4f6; }
```

### HTML 结构变更（index.html）

- 左侧栏头部添加折叠箭头图标 `◀`
- 左右侧栏各添加一个边缘折叠按钮（`<button class="collapse-btn">`）
- 左侧栏边缘按钮在右侧边缘，右侧栏边缘按钮在左侧边缘

### 交互模块（collapse.js，新增）

- 遵循项目 IIFE + window 暴露模式
- 通过 `localStorage` 键 `__CARD_PANEL_STATE__` 持久化状态
- 提供 `PanelToggle.toggleSidebar()` 和 `PanelToggle.toggleRightbar()` 公开接口
- DOMContentLoaded 时自动恢复上次的折叠状态

### 加载顺序

`collapse.js` 插入在 `state.js` 之后、`sidebar.js` 之前：

```
state.js → collapse.js (新增) → sidebar.js → card-view.js → flashcard.js → plan.js → reorder.js → fill-blank.js → app.js
```

## 数据流

```
用户点击头部/边缘按钮
    → toggleSidebar() / toggleRightbar()
      → 切换 DOM 元素的 .collapsed 类
      → 更新边缘按钮图标（◀/▶）
      → 写入 localStorage
```

页面加载时：
```
DOMContentLoaded
    → 从 localStorage 读取 __CARD_PANEL_STATE__
    → 根据状态添加/移除 .collapsed 类
    → 设置边缘按钮图标
```

## 注意事项

1. 右侧栏的边缘折叠按钮必须放在 `.rightbar-mode` 之前（作为第一个子元素），这样折叠时整个窄条可点击展开
2. `.rightbar-mode` 自身已有 JS 控制的模式切换（badge/select 互切），折叠点击事件应绑定在 `.rightbar-mode` 容器上而非内部元素，避免冲突
3. 生成器模板（`generate_app.py`）需要同步更新 HTML 模板和 CSS 模板，确保新生成的卡包也包含此功能