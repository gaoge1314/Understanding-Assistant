/* ============================
   入口模块：初始化 + Tab + 右键工具
   ============================ */
(function() {
  'use strict';

  /* ---------- 数据加载 ---------- */
  async function loadData() {
    try {
      if (!window.__CARD_DATA__) {
        var resp = await fetch('data.json');
        if (!resp.ok) throw new Error('无法加载 data.json');
        window.__CARD_DATA__ = await resp.json();
      }
      var data = window.__CARD_DATA__;
      var APP = window.__APP__;
      APP.cardData = data.cards || [];
      APP.allTitles = data.all_knowledge_titles || [];
      APP.subject = data.subject || '知识卡包';

      document.getElementById('appTitle').textContent = '📚 ' + APP.subject;
      document.getElementById('cardCount').textContent = APP.cardData.length + ' 张';

      if (!APP.state.cardOrder || APP.state.cardOrder.length !== APP.cardData.length) {
        APP.state.cardOrder = APP.cardData.map(function(_, i) { return i; });
      }
      return true;
    } catch (e) {
      document.getElementById('contentPlaceholder').innerHTML = '<p style="color:#ef4444;">加载失败：' + e.message + '</p>';
      return false;
    }
  }

  /* ---------- Tab 导航 ---------- */
  function initTabs() {
    document.getElementById('tabNav').addEventListener('click', function(e) {
      var btn = e.target.closest('.tab-btn');
      if (!btn) return;

      var viewName = btn.dataset.view;
      document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      document.querySelectorAll('.view').forEach(function(v) { v.classList.remove('active'); });
      document.getElementById('view' + viewName.charAt(0).toUpperCase() + viewName.slice(1)).classList.add('active');

      if (viewName === 'flashcard') Flashcard.initFlashcardView();
      if (viewName === 'review') renderReviewView();
    });
  }

  /* ---------- 复习视图 ---------- */
  function renderReviewView() {
    var view = document.getElementById('reviewView');
    var today = new Date().toISOString().split('T')[0];
    var APP = window.__APP__;
    var order = APP.state.cardOrder;

    var greenCount = 0, yellowCount = 0, redCount = 0;
    var rows = [];

    order.forEach(function(cid) {
      var card = APP.cardData[cid];
      if (!card) return;
      var rec = AppState.getReviewRecord(card.title);

      var status, info;
      if (rec.level >= 4 && rec.nextReviewDate > today) {
        status = 'green';
        info = '熟悉（Level ' + rec.level + '，下次 ' + rec.nextReviewDate + '）';
        greenCount++;
      } else if (rec.level >= 2 && rec.level <= 3) {
        status = 'yellow';
        info = '复习中（Level ' + rec.level + '，下次 ' + (rec.nextReviewDate || '-') + '）';
        yellowCount++;
      } else {
        status = 'red';
        info = rec.level === 0 ? '未学习' : '待复习（Level ' + rec.level + '，原定 ' + rec.nextReviewDate + '）';
        redCount++;
      }

      rows.push({ cardId: cid, title: card.title, status: status, info: info });
    });

    var listHtml = '<div class="review-list">';
    rows.forEach(function(r) {
      var btnText = r.status === 'green' ? '查看' : '去学习';
      listHtml += '<div class="review-item" data-card-id="' + r.cardId + '">' +
        '<span class="ri-status ' + r.status + '"></span>' +
        '<span class="ri-title">' + AppState.escapeHtml(r.title) + '</span>' +
        '<span class="ri-info">' + r.info + '</span>' +
        '<button class="review-btn" data-card-id="' + r.cardId + '">' + btnText + '</button>' +
        '</div>';
    });
    listHtml += '</div>';

    view.innerHTML = [
      '<div class="review-header">',
        '<h2>📅 复习概览 — ' + APP.subject + '</h2>',
        '<div class="sub">今日日期：' + today + '</div>',
      '</div>',
      '<div class="review-stats">',
        '<div class="stat-card"><div class="stat-num" style="color:#22c55e;">' + greenCount + '</div><div class="stat-label">🟢 熟悉</div></div>',
        '<div class="stat-card"><div class="stat-num" style="color:#f59e0b;">' + yellowCount + '</div><div class="stat-label">🟡 复习中</div></div>',
        '<div class="stat-card"><div class="stat-num" style="color:#ef4444;">' + redCount + '</div><div class="stat-label">🔴 遗忘/未学</div></div>',
        '<div class="stat-card"><div class="stat-num" style="color:#9ca3af;">' + (greenCount + yellowCount + redCount) + '</div><div class="stat-label">📊 总计</div></div>',
      '</div>',
      listHtml
    ].join('');

    /* 复习条目点击跳转 */
    view.addEventListener('click', function(e) {
      var btn = e.target.closest('.review-btn');
      if (!btn) return;
      var cardId = parseInt(btn.dataset.cardId);
      if (isNaN(cardId)) return;
      document.querySelector('.tab-btn[data-view="learn"]').click();
      CardView.selectCard(cardId);
    });
  }

  /* ============================================================
     重构模式切换
     ============================================================ */
  document.getElementById('reconstructSelect').addEventListener('change', function() {
    var APP = window.__APP__;
    var card = APP.cardData[APP.currentCardIndex];
    if (!card) return;
    var mode = this.value;
    document.getElementById('reorderArea').style.display = 'none';
    document.getElementById('fillArea').style.display = 'none';

    if (mode === 'reorder') {
      document.getElementById('reorderArea').style.display = 'block';
      Reorder.initReorder(card);
    } else if (mode === 'fill-blank') {
      document.getElementById('fillArea').style.display = 'block';
      FillBlank.initFillBlank(card);
    }
  });

  /* ============================================================
     左侧栏底部按钮
     ============================================================ */
  document.getElementById('btnAddGroup').addEventListener('click', function() {
    var name = prompt('请输入分组名称：');
    if (!name || !name.trim()) return;
    var APP = window.__APP__;
    if (!APP.state.groups) APP.state.groups = [];
    APP.state.groups.push({ name: name.trim(), cardIds: [] });
    AppState.saveState();
    Sidebar.renderSidebar();
  });

  document.getElementById('btnReset').addEventListener('click', function() {
    if (!confirm('恢复默认卡片顺序？')) return;
    var APP = window.__APP__;
    APP.state.cardOrder = APP.cardData.map(function(_, i) { return i; });
    APP.state.groups = [];
    AppState.saveState();
    Sidebar.renderSidebar();
    if (APP.currentCardIndex >= 0) CardView.selectCard(APP.currentCardIndex);
  });

  document.getElementById('btnAskAI').addEventListener('click', function() {
    var APP = window.__APP__;
    var card = APP.currentCardIndex >= 0 ? APP.cardData[APP.currentCardIndex] : null;
    var cardName = card ? card.title : '未知';
    alert('请在 Trae 对话中告诉我：\n\n"我正在学习「' + cardName + '」这张卡片，帮我理解一下"\n\n学习应用 Agent 会为你提供辅导。');
  });

  /* ============================================================
     初始化
     ============================================================ */
  async function init() {
    AppState.loadState();
    var ok = await loadData();
    if (!ok) return;

    initTabs();
    Sidebar.renderSidebar();

    var APP = window.__APP__;
    if (APP.cardData.length > 0) {
      CardView.selectCard(APP.state.cardOrder[0] || 0);
    }

    window.addEventListener('beforeunload', AppState.saveState);
  }

  init();
})();