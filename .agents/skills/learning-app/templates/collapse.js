/* ============================
   模块：侧栏折叠/展开控制
   ============================ */
(function() {
  'use strict';

  /* ---- 展开/折叠图标 ---- */
  var ICON_EXPAND = '▶';
  var ICON_COLLAPSE = '◀';
  var SIDEBAR_HEADER_ARROW = '◀';

  /* ---- 切换左侧栏 ---- */
  function toggleSidebar() {
    var el = document.getElementById('sidebar');
    if (!el) return;
    var collapsed = el.classList.toggle('collapsed');
    /* 更新边缘按钮图标 */
    var edgeBtn = document.getElementById('sidebarEdgeBtn');
    if (edgeBtn) edgeBtn.textContent = collapsed ? ICON_EXPAND : ICON_COLLAPSE;
    /* 持久化 */
    var APP = window.__APP__;
    if (APP && APP.state) {
      APP.state.sidebarCollapsed = collapsed;
      if (window.AppState) AppState.saveState();
    }
  }

  /* ---- 切换右侧栏 ---- */
  function toggleRightbar() {
    var el = document.getElementById('rightbar');
    if (!el) return;
    var collapsed = el.classList.toggle('collapsed');
    var edgeBtn = document.getElementById('rightbarEdgeBtn');
    if (edgeBtn) edgeBtn.textContent = collapsed ? ICON_COLLAPSE : ICON_EXPAND;
    var APP = window.__APP__;
    if (APP && APP.state) {
      APP.state.rightbarCollapsed = collapsed;
      if (window.AppState) AppState.saveState();
    }
  }

  /* ---- 从 AppState 恢复折叠状态 ---- */
  function restoreFromState() {
    var APP = window.__APP__;
    if (!APP || !APP.state) return;

    /* 左侧栏 */
    var sidebar = document.getElementById('sidebar');
    var sidebarEdgeBtn = document.getElementById('sidebarEdgeBtn');
    if (sidebar && sidebarEdgeBtn) {
      if (APP.state.sidebarCollapsed) {
        sidebar.classList.add('collapsed');
        sidebarEdgeBtn.textContent = ICON_EXPAND;
      } else {
        sidebar.classList.remove('collapsed');
        sidebarEdgeBtn.textContent = ICON_COLLAPSE;
      }
    }

    /* 右侧栏 */
    var rightbar = document.getElementById('rightbar');
    var rightbarEdgeBtn = document.getElementById('rightbarEdgeBtn');
    if (rightbar && rightbarEdgeBtn) {
      if (APP.state.rightbarCollapsed) {
        rightbar.classList.add('collapsed');
        rightbarEdgeBtn.textContent = ICON_COLLAPSE;
      } else {
        rightbar.classList.remove('collapsed');
        rightbarEdgeBtn.textContent = ICON_EXPAND;
      }
    }
  }

  /* ---- 绑定事件 ---- */
  function bindEvents() {
    /* 左侧栏：头部点击 + 边缘按钮 */
    var sidebarHeader = document.querySelector('.sidebar-header');
    if (sidebarHeader) {
      sidebarHeader.addEventListener('click', function(e) {
        /* 如果点击的是按钮或图标内部，不重复触发 */
        if (e.target.closest('.collapse-btn') || e.target.closest('#sidebarCollapseIcon')) return;
        toggleSidebar();
      });
    }
    var sidebarEdgeBtn = document.getElementById('sidebarEdgeBtn');
    if (sidebarEdgeBtn) {
      sidebarEdgeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleSidebar();
      });
    }

    /* 右侧栏：头部点击（排除 select）+ 边缘按钮 */
    var rightbarMode = document.querySelector('.rightbar-mode');
    if (rightbarMode) {
      rightbarMode.addEventListener('click', function(e) {
        if (e.target.tagName === 'SELECT') return;
        if (e.target.closest('.collapse-btn')) return;
        toggleRightbar();
      });
    }
    var rightbarEdgeBtn = document.getElementById('rightbarEdgeBtn');
    if (rightbarEdgeBtn) {
      rightbarEdgeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleRightbar();
      });
    }
  }

  /* ---- 初始化 ---- */
  function init() {
    /* 等待 AppState.state 加载完成 */
    var APP = window.__APP__;
    if (APP && APP.state) {
      restoreFromState();
      bindEvents();
      return;
    }
    /* 如果 state 还没加载，延迟重试 */
    var retries = 0;
    var timer = setInterval(function() {
      retries++;
      var a = window.__APP__;
      if (a && a.state) {
        clearInterval(timer);
        restoreFromState();
        bindEvents();
      } else if (retries > 20) {
        clearInterval(timer);
        /* 超时后仍然绑定事件，使用默认展开状态 */
        bindEvents();
      }
    }, 50);
  }

  /* DOM 就绪后启动 */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ---- 公开 API ---- */
  window.Collapser = {
    toggleSidebar: toggleSidebar,
    toggleRightbar: toggleRightbar,
    collapseSidebar: function() {
      var el = document.getElementById('sidebar');
      if (el && !el.classList.contains('collapsed')) toggleSidebar();
    },
    expandSidebar: function() {
      var el = document.getElementById('sidebar');
      if (el && el.classList.contains('collapsed')) toggleSidebar();
    },
    collapseRightbar: function() {
      var el = document.getElementById('rightbar');
      if (el && !el.classList.contains('collapsed')) toggleRightbar();
    },
    expandRightbar: function() {
      var el = document.getElementById('rightbar');
      if (el && el.classList.contains('collapsed')) toggleRightbar();
    }
  };
})();